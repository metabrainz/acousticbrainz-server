import db

def create(musicbrainz_id):
    with db.engine.connect() as connection:
        result = connection.execute(
            """INSERT INTO "user" (musicbrainz_id)
                    VALUES (%s)
                 RETURNING id""", (musicbrainz_id,))
        new_id = result.fetchone()[0]
        return new_id


def get(id):
    """Get user with a specified ID (integer)."""
    with db.engine.connect() as connection:
        result = connection.execute('SELECT id, created, musicbrainz_id FROM "user" WHERE id = %s',
                       (id,))
        row = result.fetchone()
        return dict(row) if row else None


def get_by_mb_id(musicbrainz_id):
    """Get user with a specified MusicBrainz ID (username).
    Usernames are case-insensitive matched.
    """
    with db.engine.connect() as connection:
        result = connection.execute(
            'SELECT id, created, musicbrainz_id '
            'FROM "user" '
            'WHERE LOWER(musicbrainz_id) = LOWER(%s)',
            (musicbrainz_id,)
        )
        row = result.fetchone()
        return dict(row) if row else None


def get_or_create(musicbrainz_id):
    """Return a user row for the given username, creating it
    if it does not exist.
    """
    user = get_by_mb_id(musicbrainz_id)
    if not user:
        create(musicbrainz_id)
        user = get_by_mb_id(musicbrainz_id)
    return user
