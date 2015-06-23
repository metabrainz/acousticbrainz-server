from flask_login import UserMixin


def create(musicbrainz_id):
    from acousticbrainz.data import connection
    with connection.cursor() as cursor:
        # TODO(roman): Do we need to make sure that musicbrainz_id is case insensitive?
        cursor.execute('INSERT INTO "user" (musicbrainz_id) VALUES (%s) RETURNING id',
                       (musicbrainz_id,))
        connection.commit()
        new_id = cursor.fetchone()[0]
        return new_id


def get(id):
    """Get user with a specified ID (integer)."""
    from acousticbrainz.data import connection
    with connection.cursor() as cursor:
        cursor.execute('SELECT id, created, musicbrainz_id FROM "user" WHERE id = %s',
                       (id,))
        row = cursor.fetchone()
        if row:
            return User(
                id=row[0],
                created=row[1],
                musicbrainz_id=row[2],
            )
        else:
            return None


def get_by_mb_id(musicbrainz_id):
    """Get user with a specified MusicBrainz ID."""
    from acousticbrainz.data import connection
    with connection.cursor() as cursor:
        cursor.execute(
            'SELECT id, created, musicbrainz_id '
            'FROM "user" '
            'WHERE LOWER(musicbrainz_id) = LOWER(%s)',
            (musicbrainz_id,)
        )
        row = cursor.fetchone()
        if row:
            return User(
                id=row[0],
                created=row[1],
                musicbrainz_id=row[2],
            )
        else:
            return None


def get_or_create(musicbrainz_id):
    user = get_by_mb_id(musicbrainz_id)
    if not user:
        create(musicbrainz_id)
        user = get_by_mb_id(musicbrainz_id)
    return user


class User(UserMixin):
    def __init__(self, id, created, musicbrainz_id):
        self.id = id
        self.created = created
        self.musicbrainz_id = musicbrainz_id
