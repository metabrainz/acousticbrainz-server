#!/usr/bin/env python
import json
import psycopg2
import logging
import config
import uuid
import datetime
import time
from operator import itemgetter
from logging.handlers import RotatingFileHandler
from flask import Flask, request, Response, jsonify, render_template
from werkzeug.exceptions import BadRequest, ServiceUnavailable, NotFound, InternalServerError
import memcache
from hashlib import sha256

SANITY_CHECK_KEYS = [
   [ 'metadata', 'version', 'essentia' ],
   [ 'metadata', 'version', 'essentia_git_sha' ],
   [ 'metadata', 'version', 'extractor' ],
   [ 'metadata', 'version', 'essentia_build_sha' ],
   [ 'metadata', 'audio_properties', 'length' ],
   [ 'metadata', 'audio_properties', 'bit_rate' ],
   [ 'metadata', 'audio_properties', 'codec' ],
   [ 'metadata', 'audio_properties', 'lossless' ],
   [ 'metadata', 'tags', 'file_name' ],
   [ 'metadata', 'tags', 'musicbrainz_recordingid' ],
   [ 'lowlevel' ],
   [ 'rhythm' ],
   [ 'tonal' ],
]
STATS_CACHE_TIMEOUT = 60 * 10 # ten minutes
MAX_NUMBER_DUPES     = 5

STATIC_PATH = "/static"
STATIC_FOLDER = "../static"
TEMPLATE_FOLDER = "../templates"

app = Flask(__name__,
            static_url_path = STATIC_PATH,
            static_folder = STATIC_FOLDER,
            template_folder = TEMPLATE_FOLDER)

# Configuration
app.config.from_object(config)

# Error handling and logging
handler = RotatingFileHandler(config.LOG_FILE)
handler.setLevel(logging.INFO)
app.logger.addHandler(handler)

def validate_uuid(string, version=4):
    """Validates UUID of a specified version (default version is 4).

    Returns:
        True if UUID is valid.
        False otherwise.
    """
    try:
        _ = uuid.UUID(string, version=version)
    except ValueError:
        return False
    return True

def has_key(dict, keys):
    for k in keys:
        if not dict.has_key(k):
            return False
        dict = dict[k]
    return True

def sanity_check_json(data):
    for check in SANITY_CHECK_KEYS:
        if not has_key(data, check):
            return "key '%s' was not found in submitted data." % ' : '.join(check)
    return ""

def json_error(err):
    return json.dumps(dict(error=err))

@app.route("/")
def index():
    mc = memcache.Client(['127.0.0.1:11211'], debug=0)
    stats_keys = ["lowlevel-lossy", "lowlevel-lossy-unique", "lowlevel-lossless", "lowlevel-lossless-unique"]
    stats = mc.get_multi(stats_keys, key_prefix="ac-num-")
    last_collected = mc.get('last-collected')

    # Recalculate everything together, always.
    if sorted(stats_keys) != sorted(stats.keys()) or last_collected is None:
        stats_parameters = dict([(a, 0) for a in stats_keys])

        conn = psycopg2.connect(config.PG_CONNECT)
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

    return render_template("index.html", stats=value, last_collected=last_collected)

@app.route("/statistics-graph")
def statistics_graph():
    return render_template("statistics-graph.html")

@app.route("/statistics-data")
def statistics_data():
    conn = psycopg2.connect(config.PG_CONNECT)
    cur = conn.cursor()
    cur.execute("SELECT name, array_agg(collected ORDER BY collected ASC) AS times, array_agg(value ORDER BY collected ASC) AS values FROM statistics GROUP BY name");
    stats_key_map = {
        "lowlevel-lossy": "Lossy (all)",
        "lowlevel-lossy-unique": "Lossy (unique)",
        "lowlevel-lossless": "Lossless (all)",
        "lowlevel-lossless-unique": "Lossless (unique)"
    }
    ret = []
    total_unique = {"key": "Total (unique)", "values": {}}
    total_all = {"key": "Total (all)", "values": {}}
    for val in cur:
        pairs = zip([make_timestamp(v) for v in val[1]], val[2])
        ret.append({"key": stats_key_map.get(val[0], val[0]), "values": [{'x': v[0], 'y': v[1]} for v in pairs]})
        second = {}
        if val[0] in ["lowlevel-lossy", "lowlevel-lossless"]:
            second = total_all
        elif val[0] in ["lowlevel-lossy-unique", "lowlevel-lossless-unique"]:
            second = total_unique
        for pair in pairs:
            if pair[0] in second['values']:
                second['values'][pair[0]] = second['values'][pair[0]] + pair[1]
            else:
                second['values'][pair[0]] = pair[1]

    total_unique['values'] = [{'x': k, 'y': total_unique['values'][k]} for k in sorted(total_unique['values'].keys())]
    total_all['values'] = [{'x': k, 'y': total_all['values'][k]} for k in sorted(total_all['values'].keys())]
    ret.extend([total_unique, total_all])
    return Response(json.dumps(sorted(ret, key=itemgetter('key'))), content_type='application/json; charset=utf-8')

def make_timestamp(dt):
    return time.mktime(dt.utctimetuple()) * 1000

@app.route("/download")
def download():
    return render_template("download.html")

@app.route("/contribute")
def contribute():
    return render_template("contribute.html")

@app.route("/sample-data")
def sample_data():
    return render_template("sample-data.html")

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/api")
def api():
    return render_template("api.html")

@app.route("/<mbid>/low-level", methods=["POST"])
def submit_low_level(mbid):
    """Endpoint for submitting low-level information to AcousticBrainz"""

    raw_data = request.get_data()
    try:
        data = json.loads(raw_data)
    except ValueError, e:
        raise BadRequest("Cannot parse JSON document: %s" % e)

    try:
        # if the user submitted a trackid key, rewrite to recording_id
        if data['metadata']['tags'].has_key("musicbrainz_trackid"):
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

    if not validate_uuid(mbid):
        raise BadRequest("Invalid MBID: %s" % mbid)


    # Ensure the MBID form the URL matches the recording_id from the POST data
    if data['metadata']['tags']["musicbrainz_recordingid"][0].lower() != mbid.lower():
        raise BadRequest("The musicbrainz_trackid/musicbrainz_recordingid in the submitted data does not match "
                         "the MBID that is part of this resource URL.")

    # The data looks good, lets see about saving it
    is_lossless_submit = data['metadata']['audio_properties']['lossless']
    build_sha1 = data['metadata']['version']['essentia_build_sha']
    data_json = json.dumps(data, sort_keys=True, separators=(',', ':'))
    data_sha256 = sha256(data_json).hexdigest()

    conn = psycopg2.connect(config.PG_CONNECT)
    cur = conn.cursor()
    try:
        # Checking to see if we already have this data
        cur.execute("SELECT data_sha256 FROM lowlevel WHERE mbid = %s", (mbid, ))

        # if we don't have this data already, add it
        sha_values = [v[0] for v in cur.fetchall()]

        if not data_sha256 in sha_values:
            app.logger.info("Saved %s" % mbid)
            cur.execute("INSERT INTO lowlevel (mbid, build_sha1, data_sha256, lossless, data)"
                        "VALUES (%s, %s, %s, %s, %s)",
                        (mbid, build_sha1, data_sha256, is_lossless_submit, data_json))
            conn.commit()
            return ""

        app.logger.info("Already have %s" % data_sha256)

    except psycopg2.ProgrammingError, e:
        raise BadRequest(str(e))
    except psycopg2.IntegrityError, e:
        raise BadRequest(str(e))
    except psycopg2.OperationalError, e:
        raise ServiceUnavailable(str(e))

    return ""

@app.route("/<mbid>/low-level", methods=["GET"])
def get_low_level(mbid):
    """Endpoint for fetching low-level information to AcousticBrainz"""

    if not validate_uuid(mbid):
        raise BadRequest("Invalid MBID: %s" % mbid)

    conn = psycopg2.connect(config.PG_CONNECT)
    cur = conn.cursor()
    try:
        cur.execute("SELECT data::text FROM lowlevel WHERE mbid = %s", (mbid, ))
        if not cur.rowcount:
            raise NotFound

        row = cur.fetchone()
        return Response(row[0], content_type='application/json')

    except psycopg2.IntegrityError, e:
        raise BadRequest(str(e))
    except psycopg2.OperationalError, e:
        raise ServiceUnavailable(str(e))

    return InternalServerError("whoops, looks like a cock-up on our part!")

@app.route("/<mbid>/high-level", methods=["GET"])
def get_high_level(mbid):
    """Endpoint for fetching high-level information to AcousticBrainz"""

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
        return Response(row[0], content_type='application/json')

    except psycopg2.IntegrityError, e:
        raise BadRequest(str(e))
    except psycopg2.OperationalError, e:
        raise ServiceUnavailable(str(e))

    return InternalServerError("Bummer, dude.")

@app.route("/<mbid>", methods=["GET"])
def get_summary(mbid):

    if not validate_uuid(mbid):
        raise BadRequest("Invalid MBID: %s" % mbid)

    conn = psycopg2.connect(config.PG_CONNECT)
    cur = conn.cursor()
    try:
        cur.execute("""SELECT ll.data, hlj.data 
                         FROM highlevel hl, lowlevel ll, highlevel_json hlj
                        WHERE hl.data = hlj.id 
                          AND hl.id = ll.id
                          AND ll.mbid = %s""", (mbid, ))
        if not cur.rowcount:
            return render_template("summary.html", mbid="")

        row = cur.fetchone()
        print row[0]
        return render_template("summary.html", lowlevel=row[0], highlevel=row[1], mbid=mbid)

    except psycopg2.IntegrityError, e:
        raise BadRequest(str(e))
    except psycopg2.OperationalError, e:
        raise ServiceUnavailable(str(e))

    return InternalServerError("whoops!")

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8080)
