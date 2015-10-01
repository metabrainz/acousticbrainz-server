import db

def create(musicbrainz_id):
    with db.get_connection() as connection:
        # TODO(roman): Do we need to make sure that musicbrainz_id is case insensitive?
        result = connection.execute('INSERT INTO "user" (musicbrainz_id) VALUES (%s) RETURNING id',
                       (musicbrainz_id,))
        new_id = result.fetchone()[0]
        return new_id


def get(id):
    """Get user with a specified ID (integer)."""
    with db.get_connection() as connection:
        result = connection.execute('SELECT id, created, musicbrainz_id FROM "user" WHERE id = %s',
                       (id,))
        row = result.fetchone()
        return dict(row) if row else None


def get_by_mb_id(musicbrainz_id):
    """Get user with a specified MusicBrainz ID."""
    with db.get_connection() as connection:
        result = connection.execute(
            'SELECT id, created, musicbrainz_id '
            'FROM "user" '
            'WHERE LOWER(musicbrainz_id) = LOWER(%s)',
            (musicbrainz_id,)
        )
        row = result.fetchone()
        return dict(row) if row else None


def get_or_create(musicbrainz_id):
    user = get_by_mb_id(musicbrainz_id)
    if not user:
        create(musicbrainz_id)
        user = get_by_mb_id(musicbrainz_id)
    return user
