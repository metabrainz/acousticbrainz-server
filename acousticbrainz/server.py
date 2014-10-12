#!/usr/bin/env python
import json
import psycopg2
import logging
import config
import uuid
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
    stats_keys = ["lossy", "lossy-unique", "lossless", "lossless-unique"]
    stats = mc.get_multi(stats_keys, key_prefix="ac-num-")

    # Always recalculate and update all stats at once.
    if sorted(stats_keys) != sorted(stats.keys()):
        stats_parameters = dict([(a, 0) for a in stats_keys])
        conn = psycopg2.connect(config.PG_CONNECT)
        cur = conn.cursor()

        cur.execute("SELECT lossless, count(*) FROM lowlevel GROUP BY lossless")
        for row in cur.fetchall():
            if row[0]: stats_parameters['lossless'] = row[1]
            if not row[0]: stats_parameters['lossy'] = row[1]

        cur.execute("SELECT lossless, count(*) FROM (SELECT DISTINCT ON (mbid) mbid, lossless FROM lowlevel ORDER BY mbid, lossless DESC) q GROUP BY lossless;")
        for row in cur.fetchall():
            if row[0]: stats_parameters['lossless-unique'] = row[1]
            if not row[0]: stats_parameters['lossy-unique'] = row[1]

        mc.set_multi(stats_parameters, key_prefix="ac-num-", time=STATS_CACHE_TIMEOUT)
    else:
        stats_parameters = stats

    return render_template("index.html", stats=stats_parameters)

@app.route("/download")
def download():
    return render_template("download.html")

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
    except KeyError:
        pass

    # sanity check the incoming data
    err = sanity_check_json(data)
    if err:
        raise BadRequest(err)

    if not validate_uuid(mbid):
        raise BadRequest("Invalid MBID: %s" % e)


    # Ensure the MBID form the URL matches the recording_id from the POST data
    if data['metadata']['tags']["musicbrainz_recordingid"][0].lower() != mbid.lower():
        raise BadRequest("The musicbrainz_trackid/musicbrainz_recordingid in the submitted data does not match "
                         "the MBID that is part of this resource URL.")

    # The data looks good, lets see about saving it
    is_lossless_submit = data['metadata']['audio_properties']['lossless']
    build_sha1 = data['metadata']['version']['essentia_build_sha']

    data_keys = ['main_data', 'metadata_version', 'metadata_audio', 'metadata_tags']
    split_data = dict([(k, ("", "")) for k in data_keys])

    split_data['main_data'][1] = json.dumps(dict([(k, data[k]) for k in data.keys() if k != 'metadata']), sort_keys=True, separators=(',', ':'))
    split_data['metadata_version'][1] = json.dumps(data['metadata']['version'], sort_keys=True, separators=(',', ':'))
    split_data['metadata_audio'][1] = json.dumps(data['metadata']['audio_properties'], sort_keys=True, separators=(',', ':'))
    split_data['metadata_tags'][1] = json.dumps(data['metadata']['tags'], sort_keys=True, separators=(',', ':'))

    for k in split_data.keys():
        split_data[k][0] = sha256(split_data[k][1]).hexdigest()

    conn = psycopg2.connect(config.PG_CONNECT)
    cur = conn.cursor()
    try:
        cur.execute("SELECT data_sha256, id from raw_json WHERE data_sha256 IN (%s, %s, %s, %s)",
                    tuple([data[k][0] for k in split_data.keys()]))
        existing_data = dict([(row[0], row[1]) for row in cur.fetchall()])

        for name, value in split_data.iteritems():
            (data_sha256, json_data) = value
            if existing_data.get(data_sha256) is None:
                cur.execute("INSERT INTO raw_json (data_sha256, data) VALUES (%s, %s) RETURNING id",
                            (data_sha256, json_data))
                existing_data[data_sha256] = cur.fetchone()[0]

        vals = [existing_data[data[key][0]] for key in data_keys]
        cur.execute(
            """SELECT id FROM lowlevel_data
                WHERE main_data = %s
                  AND metadata_version = %s
                  AND metadata_audio = %s
                  AND metadata_tags = %s""",
            tuple(vals)
        )

        if cur.rowcount == 0:
            # If no ID exists, insert a new one
            cur.execute(
                """INSERT INTO lowlevel_data
                       (main_data, metadata_version, metadata_audio, metadata_tags)
                       VALUES (%s, %s, %s, %s) RETURNING id""",
                tuple(vals)
            )
        data_id = cur.fetchone()[0]

        cur.execute("SELECT TRUE FROM lowlevel WHERE mbid = %s, build_sha1 = %s, lossless = %s, data = %s",
                    (mbid, build_sha1, is_lossless_submit, data_id))
        if cur.rowcount == 0:
            app.logger.info("Saved %s" % mbid)
            cur.execute("INSERT INTO lowlevel (mbid, build_sha1, lossless, data)"
                        "VALUES (%s, %s, %s, %s)",
                        (mbid, build_sha1, is_lossless_submit, data_id))
            conn.commit()
            return ""
        else:
            app.logger.info("Already have %s" % mbid)

    except psycopg2.IntegrityError, e:
        raise BadRequest(str(e))
    except psycopg2.OperationalError, e:
        raise ServiceUnavailable(str(e))

    return ""

@app.route("/<mbid>/low-level", methods=["GET"])
def get_low_level(mbid):
    """Endpoint for fetching low-level information to AcousticBrainz"""

    if not validate_uuid(mbid):
        raise BadRequest("Invalid MBID: %s" % e)

    conn = psycopg2.connect(config.PG_CONNECT)
    cur = conn.cursor()
    try:
        cur.execute("SELECT json::text FROM lowlevel JOIN lowlevel_data_json ON lowlevel.id = lowlevel_data_json.id WHERE mbid = %s", (mbid, ))
        if not cur.rowcount:
            raise NotFound

        row = cur.fetchone()
        return Response(row[0], content_type='application/json')

    except psycopg2.IntegrityError, e:
        raise BadRequest(str(e))
    except psycopg2.OperationalError, e:
        raise ServiceUnavailable(str(e))

    return InternalServerError("whoops, looks like a cock-up on our part!")

if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=8080)
