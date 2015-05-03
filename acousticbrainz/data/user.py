import psycopg2
from flask import current_app
from flask_login import UserMixin
from werkzeug.exceptions import BadRequest, ServiceUnavailable


def create(musicbrainz_id):
    try:
        connection = psycopg2.connect(current_app.config['PG_CONNECT'])
        cursor = connection.cursor()
        # TODO(roman): Do we need to make sure that musicbrainz_id is case insensitive?
        cursor.execute('INSERT INTO "user" (musicbrainz_id) VALUES (%s) RETURNING id',
                       (musicbrainz_id,))
        connection.commit()
        new_id = cursor.fetchone()[0]
    except psycopg2.ProgrammingError as e:
        raise BadRequest(e)
    except psycopg2.IntegrityError as e:
        raise BadRequest(e)
    except psycopg2.OperationalError as e:
        raise ServiceUnavailable(e)

    return new_id


def get(id):
    """Get user with a specified ID (integer)."""
    try:
        connection = psycopg2.connect(current_app.config['PG_CONNECT'])
        cursor = connection.cursor()
        cursor.execute('SELECT id, created, musicbrainz_id FROM "user" WHERE id = %s',
                       (id,))
    except psycopg2.IntegrityError as e:
        raise BadRequest(e)
    except psycopg2.OperationalError as e:
        raise ServiceUnavailable(e)

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
    try:
        connection = psycopg2.connect(current_app.config['PG_CONNECT'])
        cursor = connection.cursor()
        cursor.execute("""SELECT id, created, musicbrainz_id
                          FROM "user"
                          WHERE LOWER(musicbrainz_id) = LOWER(%s)""",
                       (musicbrainz_id,))
    except psycopg2.IntegrityError as e:
        raise BadRequest(e)
    except psycopg2.OperationalError as e:
        raise ServiceUnavailable(e)

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
