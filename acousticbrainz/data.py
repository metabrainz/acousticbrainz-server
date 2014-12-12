import psycopg2
from acousticbrainz.utils import sanity_check_json, clean_metadata, interpret_high_level
from werkzeug.exceptions import BadRequest, ServiceUnavailable, InternalServerError, NotFound
from flask import current_app
from hashlib import sha256
import datetime
import memcache
import json
import time


STATS_CACHE_TIMEOUT = 60 * 10  # ten minutes
LAST_MBIDS_CACHE_TIMEOUT = 60  # 1 minute (this query is cheap)


def submit_low_level(mbid, data):
    """Function for submitting low-level data.

    Args:
        mbid: MusicBrainz ID of the track that corresponds to the data that is
            being submitted.
        data: Low level data about the track.
    """
    mbid = str(mbid)
    data = clean_metadata(data)

    try:
        # If the user submitted a trackid key, rewrite to recording_id
        if "musicbrainz_trackid" in data['metadata']['tags']:
            val = data['metadata']['tags']["musicbrainz_trackid"]
            del data['metadata']['tags']["musicbrainz_trackid"]
            data['metadata']['tags']["musicbrainz_recordingid"] = val

        if data['metadata']['audio_properties']['lossless']:
            data['metadata']['audio_properties']['lossless'] = True
        else:
            data['metadata']['audio_properties']['lossless'] = False

    except KeyError:
        pass

    # sanity check the incoming data
    err = sanity_check_json(data)
    if err:
        raise BadRequest(err)

    # Ensure the MBID form the URL matches the recording_id from the POST data
    if data['metadata']['tags']["musicbrainz_recordingid"][0].lower() != mbid.lower():
        raise BadRequest("The musicbrainz_trackid/musicbrainz_recordingid in"
                         "the submitted data does not match the MBID that is"
                         "part of this resource URL.")

    # The data looks good, lets see about saving it
    is_lossless_submit = data['metadata']['audio_properties']['lossless']
    build_sha1 = data['metadata']['version']['essentia_build_sha']
    data_json = json.dumps(data, sort_keys=True, separators=(',', ':'))
    data_sha256 = sha256(data_json).hexdigest()

    conn = psycopg2.connect(current_app.config['PG_CONNECT'])
    cur = conn.cursor()
    try:
        # Checking to see if we already have this data
        cur.execute("SELECT data_sha256 FROM lowlevel WHERE mbid = %s", (mbid, ))

        # if we don't have this data already, add it
        sha_values = [v[0] for v in cur.fetchall()]

        if data_sha256 not in sha_values:
            current_app.logger.info("Saved %s" % mbid)
            cur.execute("INSERT INTO lowlevel (mbid, build_sha1, data_sha256, lossless, data)"
                        "VALUES (%s, %s, %s, %s, %s)",
                        (mbid, build_sha1, data_sha256, is_lossless_submit, data_json))
            conn.commit()
            return ""

        current_app.logger.info("Already have %s" % data_sha256)

    except psycopg2.ProgrammingError, e:
        raise BadRequest(str(e))
    except psycopg2.IntegrityError, e:
        raise BadRequest(str(e))
    except psycopg2.OperationalError, e:
        raise ServiceUnavailable(str(e))


def load_low_level(mbid):
    """Load low level data for a given MBID."""
    conn = psycopg2.connect(current_app.config['PG_CONNECT'])
    cur = conn.cursor()
    try:
        cur.execute("SELECT data::text FROM lowlevel WHERE mbid = %s", (str(mbid), ))
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
    """Load high level data for a given MBID."""
    conn = psycopg2.connect(current_app.config['PG_CONNECT'])
    cur = conn.cursor()
    try:
        cur.execute("""SELECT hlj.data::text
                         FROM highlevel hl
                         JOIN highlevel_json hlj
                           ON hl.data = hlj.id
                        WHERE mbid = %s""", (str(mbid), ))
        if not cur.rowcount:
            raise NotFound

        row = cur.fetchone()
        return row[0]

    except psycopg2.IntegrityError, e:
        raise BadRequest(str(e))
    except psycopg2.OperationalError, e:
        raise ServiceUnavailable(str(e))

    return InternalServerError("Bummer, dude.")


def get_summary_data(mbid):
    mbid = str(mbid)
    conn = psycopg2.connect(current_app.config['PG_CONNECT'])
    cur = conn.cursor()
    try:
        cur.execute("SELECT data FROM lowlevel WHERE mbid = %s", (mbid, ))
        if not cur.rowcount:
            raise NotFound("We do not have data for this track. Please upload it!")

        row = cur.fetchone()
        lowlevel = row[0]
        if 'artist' not in lowlevel['metadata']['tags']:
            lowlevel['metadata']['tags']['artist'] = ["[unknown]"]
        if 'release' not in lowlevel['metadata']['tags']:
            lowlevel['metadata']['tags']['release'] = ["[unknown]"]
        if 'title' not in lowlevel['metadata']['tags']:
            lowlevel['metadata']['tags']['title'] = ["[unknown]"]

        # Format track length readably (mm:ss)
        lowlevel['metadata']['audio_properties']['length_formatted'] = \
            time.strftime("%M:%S", time.gmtime(lowlevel['metadata']['audio_properties']['length']))

        cur.execute("SELECT hlj.data "
                    "FROM highlevel hl, highlevel_json hlj "
                    "WHERE hl.data = hlj.id "
                    "AND hl.mbid = %s", (mbid, ))
        genres = None
        moods = None
        other = None
        highlevel = None
        if cur.rowcount:
            row = cur.fetchone()
            highlevel = row[0]
            try:
                genres, moods, other = interpret_high_level(highlevel)
            except KeyError:
                pass

        return lowlevel, highlevel, genres, moods, other


    except psycopg2.IntegrityError, e:
        raise BadRequest(str(e))
    except psycopg2.OperationalError, e:
        raise ServiceUnavailable(str(e))

    return InternalServerError("whoops!")


def get_last_submitted_tracks():
    """Function for getting a list of recently submitted tracks.

    Returns:
        List of recently submitted tracks. Contains MBID, artist and title.
    """
    mc = memcache.Client(['127.0.0.1:11211'], debug=0)
    last_submitted_data = mc.get('last-submitted-data')
    if not last_submitted_data:
        conn = psycopg2.connect(current_app.config['PG_CONNECT'])
        cur = conn.cursor()
        cur.execute("""SELECT mbid,
                              data->'metadata'->'tags'->'artist'->>0,
                              data->'metadata'->'tags'->'title'->>0
                         FROM lowlevel
                     ORDER BY id DESC
                        LIMIT 5
                       OFFSET 10""")
        last_submitted_data = cur.fetchall()
        last_submitted_data = [
            (r[0], r[1].decode("UTF-8"), r[2].decode("UTF-8"))
            for r in last_submitted_data
        ]
        mc.set('last-submitted-data', last_submitted_data, time=LAST_MBIDS_CACHE_TIMEOUT)

    return last_submitted_data


def get_stats():
    mc = memcache.Client(['127.0.0.1:11211'], debug=0)
    stats_keys = ["lowlevel-lossy", "lowlevel-lossy-unique", "lowlevel-lossless", "lowlevel-lossless-unique"]
    stats = mc.get_multi(stats_keys, key_prefix="ac-num-")
    last_collected = mc.get('last-collected')

    # Recalculate everything together, always.
    if sorted(stats_keys) != sorted(stats.keys()) or last_collected is None:
        stats_parameters = dict([(a, 0) for a in stats_keys])

        conn = psycopg2.connect(current_app.config['PG_CONNECT'])
        cur = conn.cursor()
        cur.execute("SELECT now() as now, collected FROM statistics ORDER BY collected DESC LIMIT 1")
        update_db = False
        if cur.rowcount > 0:
            (now, last_collected) = cur.fetchone()
        if cur.rowcount == 0 or now - last_collected > datetime.timedelta(minutes=59):
            update_db = True

        cur.execute("SELECT lossless, count(*) FROM lowlevel GROUP BY lossless")
        for row in cur.fetchall():
            if row[0]: stats_parameters['lowlevel-lossless'] = row[1]
            if not row[0]: stats_parameters['lowlevel-lossy'] = row[1]

        cur.execute("SELECT lossless, count(*) FROM (SELECT DISTINCT ON (mbid) mbid, lossless FROM lowlevel ORDER BY mbid, lossless DESC) q GROUP BY lossless;")
        for row in cur.fetchall():
            if row[0]: stats_parameters['lowlevel-lossless-unique'] = row[1]
            if not row[0]: stats_parameters['lowlevel-lossy-unique'] = row[1]

        if update_db:
            for key, value in stats_parameters.iteritems():
                cur.execute("INSERT INTO statistics (collected, name, value) VALUES (now(), %s, %s) RETURNING collected", (key, value))
            conn.commit()

        cur.execute("SELECT now()")
        last_collected = cur.fetchone()[0]
        value = stats_parameters

        mc.set_multi(stats_parameters, key_prefix="ac-num-", time=STATS_CACHE_TIMEOUT)
        mc.set('last-collected', last_collected, time=STATS_CACHE_TIMEOUT)
    else:
        value = stats

    return value, last_collected
