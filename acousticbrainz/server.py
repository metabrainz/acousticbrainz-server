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
    conn = None
    mc = memcache.Client(['127.0.0.1:11211'], debug=0)
    count_lowlevel = mc.get("ac-num-lowlevel")
    if not count_lowlevel:
        conn = psycopg2.connect(config.PG_CONNECT)
        cur = conn.cursor()
        cur.execute("SELECT count(*) FROM lowlevel")
        count_lowlevel = cur.fetchone()[0]
        mc.set("ac-num-lowlevel", count_lowlevel, time=STATS_CACHE_TIMEOUT)

    count_lossless = mc.get("ac-num-lossless")
    if not count_lossless:
        if not conn:
            conn = psycopg2.connect(config.PG_CONNECT)
            cur = conn.cursor()
        cur.execute("SELECT count(*) FROM lowlevel WHERE lossless = 't'")
        count_lossless = cur.fetchone()[0]
        mc.set("ac-num-lossless", count_lossless, time=STATS_CACHE_TIMEOUT)

    count_unique = mc.get("ac-num-unique")
    if not count_unique:
        if not conn:
            conn = psycopg2.connect(config.PG_CONNECT)
            cur = conn.cursor()
        cur.execute("SELECT count(distinct mbid) FROM lowlevel")
        count_unique = cur.fetchone()[0]
        mc.set("ac-num-unique", count_unique, time=STATS_CACHE_TIMEOUT)
        
    return render_template("index.html", count_lowlevel=count_lowlevel, 
                                         count_lossless=count_lossless,
                                         count_unique=count_unique)

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

if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=8080)
