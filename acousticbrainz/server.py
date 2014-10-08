#!/usr/bin/env python
import json
import psycopg2
import logging
import config
from utils import validate_uuid
from logging.handlers import RotatingFileHandler
from flask import Flask, request, Response
from werkzeug.exceptions import BadRequest, ServiceUnavailable

app = Flask(__name__)

# Configuration
app.config.from_object(config)

# Error handling and logging
handler = RotatingFileHandler(config.LOG_FILE)
handler.setLevel(logging.WARNING)
app.logger.addHandler(handler)

@app.route("/")
def index():
    return "<html>Piss off!</html>"

@app.route("/<mbid>/low-level", methods=["POST"])
def submit_low_leval(mbid):
    """Endpoint for submitting low-level information to AcousticBrainz"""

    try:
        metadata, data = request.get_data.split("\n")
    except ValueError:
        raise BadRequest("Two JSON documents are required in the body of the POST request.")

    try:
        metadata = json.loads(metadata)
    except ValueError, e:
        raise BadRequest("Cannot parse metadata JSON document: %s" % e)

    is_lossless_submit = metadata['lossless']
    build_sha1 = metadata['build_sha1']

    try:
        data = json.loads(data)
    except ValueError, e:
        raise BadRequest("Cannot parse data JSON document: %s" % e)

    if not validate_uuid(mbid):
        raise BadRequest("Invalid MBID: %s" % e)

    conn = psycopg2.connect(config.PG_CONNECT)
    cur = conn.cursor()

    try:
        # Checking to see if we already have this data
        cur.execute("SELECT lossless FROM lowlevel WHERE mbid = %s", (mbid, ))

        # if we don't have it, add it
        if not cur.rowcount:
            cur.execute("INSERT INTO lowlevel (mbid, build_sha1, lossless, data)"
                        "VALUES (%s, %s, %s, %s)",
                        (mbid, build_sha1, is_lossless_submit, data))
            conn.commit()

        # if we have a lossy version and this submission is a lossless one, replace it
        row = cur.fetchone()
        if is_lossless_submit and not row[0]:
            cur.execute("UPDATE lowlevel (mbid, build_sha1, lossless, data, submitted)"
                        "VALUES (%s, %s, %s, %s, now())",
                        (mbid, build_sha1, is_lossless_submit, data))
            conn.commit()

    except psycopg2.IntegrityError, e:
        raise BadRequest(str(e))
    except psycopg2.OperationalError, e:
        raise ServiceUnavailable(str(e))

    return ""

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8080)
