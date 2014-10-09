#!/usr/bin/env python
import json
import psycopg2
import logging
import config
import uuid
from logging.handlers import RotatingFileHandler
from flask import Flask, request, Response, jsonify
from werkzeug.exceptions import BadRequest, ServiceUnavailable, NotFound, InternalServerError

app = Flask(__name__)

# Configuration
app.config.from_object(config)

# Error handling and logging
handler = RotatingFileHandler(config.LOG_FILE)
handler.setLevel(logging.WARNING)
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

@app.route("/")
def index():
    return "<html>Piss off!</html>"

@app.route("/<mbid>/low-level", methods=["POST"])
def submit_low_level(mbid):
    """Endpoint for submitting low-level information to AcousticBrainz"""

    raw_data = request.get_data()
    try:
        data = json.loads(raw_data)
    except ValueError, e:
        raise BadRequest("Cannot parse JSON document: %s" % e)

    try:
        is_lossless_submit = data['metadata']['audio_properties']['lossless']
        build_sha1 = data['metadata']['version']['essentia_build_sha']
    except KeyError:
        raise BadRequest("Submitted JSON document does not seem to be Essentia output.")

    if not validate_uuid(mbid):
        raise BadRequest("Invalid MBID: %s" % e)

    # if the user submitted a trackid key, rewrite to recording_id
    if data['metadata']['tags'].has_key("musicbrainz_trackid"):
        val = data['metadata']['tags']["musicbrainz_trackid"]
        del data['metadata']['tags']["musicbrainz_trackid"]
        data['metadata']['tags']["musicbrainz_recordingid"] = val

    conn = psycopg2.connect(config.PG_CONNECT)
    cur = conn.cursor()
    try:
        # Checking to see if we already have this data
        cur.execute("SELECT lossless FROM lowlevel WHERE mbid = %s", (mbid, ))

        # if we don't have it, add it
        if not cur.rowcount:
            cur.execute("INSERT INTO lowlevel (mbid, build_sha1, lossless, data)"
                        "VALUES (%s, %s, %s, %s)",
                        (mbid, build_sha1, is_lossless_submit, json.dumps(data)))
            conn.commit()
            return ""

        # if we have a lossy version and this submission is a lossless one, replace it
        row = cur.fetchone()
        if is_lossless_submit and not row[0]:
            cur.execute("UPDATE lowlevel (mbid, build_sha1, lossless, data, submitted)"
                        "VALUES (%s, %s, %s, %s, now())",
                        (mbid, build_sha1, is_lossless_submit, json.dumps(data)))
            conn.commit()
            return ""

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
