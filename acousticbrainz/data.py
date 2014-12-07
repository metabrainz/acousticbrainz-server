import psycopg2
import config
from utils import validate_uuid
from werkzeug.exceptions import BadRequest, ServiceUnavailable, NotFound, InternalServerError


def load_low_level(mbid):
    """
        Load the low level data from disk for a given mbid
    """

    if not validate_uuid(mbid):
        raise BadRequest("Invalid MBID: %s" % mbid)

    conn = psycopg2.connect(config.PG_CONNECT)
    cur = conn.cursor()
    try:
        cur.execute("SELECT data::text FROM lowlevel WHERE mbid = %s", (mbid, ))
        if not cur.rowcount:
            raise NotFound

        row = cur.fetchone()
        return row[0]

    except psycopg2.IntegrityError, e:
        raise BadRequest(str(e))
    except psycopg2.OperationalError, e:
        raise ServiceUnavailable(str(e))

    return InternalServerError("whoops, looks like a cock-up on our part!")


def load_high_level(mbid):
    """
        Load high level data
    """

    if not validate_uuid(mbid):
        raise BadRequest("Invalid MBID: %s" % mbid)

    conn = psycopg2.connect(config.PG_CONNECT)
    cur = conn.cursor()
    try:
        cur.execute("""SELECT hlj.data::text
                         FROM highlevel hl
                         JOIN highlevel_json hlj
                           ON hl.data = hlj.id
                        WHERE mbid = %s""", (mbid, ))
        if not cur.rowcount:
            raise NotFound

        row = cur.fetchone()
        return row[0]

    except psycopg2.IntegrityError, e:
        raise BadRequest(str(e))
    except psycopg2.OperationalError, e:
        raise ServiceUnavailable(str(e))

    return InternalServerError("Bummer, dude.")
