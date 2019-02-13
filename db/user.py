import db
import db.exceptions
import sqlalchemy

USER_COLUMNS = ["id", "created", "musicbrainz_id", "admin", "gdpr_agreed"]
ALL_USER_COLUMNS = ", ".join(['"user".%s' % c for c in USER_COLUMNS])


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
        result = connection.execute(sqlalchemy.text("""
            SELECT %s
              FROM "user"
             WHERE id = :id
        """ % ALL_USER_COLUMNS), {"id": id})
        row = result.fetchone()
        return dict(row) if row else None


def get_by_api_key(apikey):
    """Get the user with the specified active API key.
       If the API key doesn't exist, or if it is inactive,
       return None"""
    with db.engine.connect() as connection:
        query = sqlalchemy.text("""
            SELECT %s
              FROM "user"
              JOIN api_key
                ON api_key.owner = "user".id
             WHERE api_key.is_active = 't'
               AND value = :apikey""" % ALL_USER_COLUMNS)
        result = connection.execute(query, {"apikey": apikey})
        row = result.fetchone()
        return dict(row) if row else None


def get_by_mb_id(musicbrainz_id):
    """Get user with a specified MusicBrainz ID (username).
    Usernames are case-insensitive matched.
    """
    with db.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text("""
            SELECT %s
              FROM "user"
             WHERE LOWER(musicbrainz_id) = LOWER(:musicbrainz_id)
        """ % ALL_USER_COLUMNS), {"musicbrainz_id": musicbrainz_id})
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


def get_admins():
    with db.engine.connect() as connection:
        result = connection.execute("""
            SELECT %s
              FROM "user"
             WHERE admin = TRUE
        """ % ALL_USER_COLUMNS)
        return [dict(r) for r in result.fetchall()]


def set_admin(musicbrainz_id, admin, force=False):
    """Set admin status of a user.

    Args:
        musicbrainz_id: MusicBrainz username.
        admin: True to make user an admin, False to do the opposite.
        force: Set to True to create user with a specified MusicBrainz
            username if there's no account.
    """
    if not get_by_mb_id(musicbrainz_id):
        if force:
            create(musicbrainz_id)
        else:
            raise db.exceptions.NoDataFoundException(
                "Can't change admin status of %s because this user "
                "doesn't exist." % musicbrainz_id
            )
    with db.engine.connect() as connection:
        connection.execute(sqlalchemy.text("""
            UPDATE "user"
               SET admin = :admin
             WHERE LOWER(musicbrainz_id) = LOWER(:musicbrainz_id)
        """), {
            "musicbrainz_id": musicbrainz_id,
            "admin": admin,
        })


def agree_to_gdpr(musicbrainz_id):
    """ Update the gdpr_agreed column for user with specified MusicBrainz ID with current time.

    Args:
        musicbrainz_id (str): the MusicBrainz ID of the user
    """
    with db.engine.connect() as connection:
        try:
            connection.execute(sqlalchemy.text("""
                UPDATE "user"
                   SET gdpr_agreed = NOW()
                 WHERE LOWER(musicbrainz_id) = LOWER(:mb_id)
                """), {
                    'mb_id': musicbrainz_id,
                })
        except sqlalchemy.exc.ProgrammingError as err:
            raise db.exceptions.DatabaseException("Couldn't update gdpr agreement for user: %s" % str(err))
