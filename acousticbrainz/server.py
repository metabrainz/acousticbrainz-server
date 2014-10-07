#!/usr/bin/env python
import json
import psycopg2
import logging
import config
from utils import validate_uuid
from logging.handlers import RotatingFileHandler
from flask import Flask, request, Response
from flask.ext.jsonpify import jsonify
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
def submit_low_leval():
    """Endpoint for submitting low-level information to AcousticBrainz"""

    Only connection to albums on Spotify is supported right now.

    JSON parameters:
        user: UUID of the user who is adding new mapping.
        mbid: MusicBrainz ID of an entity that is being connected.
        spotify_uri: Spotify URI of an album that is being connected.
    """
    user = request.json["user"]
    if not validate_uuid(user):
        raise BadRequest("Incorrect user ID (UUID).")

    mbid = request.json["mbid"]
    if not validate_uuid(mbid):
        raise BadRequest("Incorrect MBID (UUID).")

    uri = request.json["spotify_uri"]
    if not uri.startswith("spotify:album:"):
        raise BadRequest("Incorrect Spotify URI. Only albums are supported right now.")

    conn = psycopg2.connect(config.PG_CONNECT)
    cur = conn.cursor()

    try:
        # Checking if mapping is already created
        cur.execute("SELECT id FROM mapping "
                    "WHERE is_deleted = FALSE "
                    "AND mbid = %s "
                    "AND spotify_uri = %s", (mbid, uri))
        if not cur.rowcount:
            # and if it's not, adding it
            cur.execute("INSERT INTO mapping (mbid, spotify_uri, cb_user, is_deleted)"
                        "VALUES (%s, %s, %s, FALSE)",
                        (mbid, uri, user))
            conn.commit()
    except psycopg2.IntegrityError, e:
        raise BadRequest(str(e))
    except psycopg2.OperationalError, e:
        raise ServiceUnavailable(str(e))

    response = Response()
    response.headers["Access-Control-Allow-Origin"] = "*"
    return response


@app.route("/mapping/vote", methods=["POST"])
@key_required
def vote():
    """Endpoint for voting against incorrect mappings.

    JSON parameters:
        user: UUID of the user who is voting.
        mbid: MusicBrainz ID of an entity that has incorrect mapping.
        spotify_uri: Spotify URI of an incorrectly mapped entity.
    """
    user = request.json["user"]
    if not validate_uuid(user):
        raise BadRequest("Incorrect user ID (UUID).")

    mbid = request.json["mbid"]
    if not validate_uuid(mbid):
        raise BadRequest("Incorrect MBID (UUID).")

    spotify_uri = request.json["spotify_uri"]

    conn = psycopg2.connect(config.PG_CONNECT)
    cur = conn.cursor()

    try:
        cur.execute("SELECT id FROM mapping WHERE mbid = %s AND spotify_uri = %s",
                    (mbid, spotify_uri))
        if not cur.rowcount:
            raise BadRequest("Can't find mapping between specified MBID and Spotify URI.")
        mapping_id = cur.fetchone()[0]

        # Checking if user have already voted
        cur.execute("SELECT id FROM mapping_vote WHERE mapping = %s AND cb_user = %s",
                    (mapping_id, user))
        if cur.rowcount:
            raise BadRequest("You already voted against this mapping.")

        cur.execute("INSERT INTO mapping_vote (mapping, cb_user) VALUES (%s, %s)",
                    (mapping_id, user))
        conn.commit()

    except psycopg2.IntegrityError, e:
        raise BadRequest(str(e))
    except psycopg2.OperationalError, e:
        raise ServiceUnavailable(str(e))

    # Check if threshold is reached. And if it is, marking mapping as deleted.
    try:
        cur.execute("SELECT * "
                    "FROM mapping_vote "
                    "JOIN mapping ON mapping_vote.mapping = mapping.id "
                    "WHERE mapping.mbid = %s AND mapping.spotify_uri = %s AND mapping.is_deleted = FALSE",
                    (mbid, spotify_uri))
        if cur.rowcount >= app.config["THRESHOLD"]:
            cur.execute("UPDATE mapping SET is_deleted = TRUE "
                        "WHERE mbid = %s AND spotify_uri = %s",
                        (mbid, spotify_uri))
            conn.commit()

    except psycopg2.IntegrityError, e:
        raise BadRequest(str(e))
    except psycopg2.OperationalError, e:
        raise ServiceUnavailable(str(e))

    response = Response()
    response.headers["Access-Control-Allow-Origin"] = "*"
    return response


@app.route("/mapping", methods=["POST"])
def mapping():
    """Endpoint for getting mappings for a MusicBrainz entity.

    JSON parameters:
        mbid: MBID of the entity that you need to find a mapping for.

    Returns:
        List with mappings to a specified MBID.
    """
    mbid = request.json["mbid"]
    if not validate_uuid(mbid):
        raise BadRequest("Incorrect MBID (UUID).")
   
    conn = psycopg2.connect(config.PG_CONNECT)
    cur = conn.cursor()

    cur.execute("SELECT spotify_uri "
                "FROM mapping "
                "WHERE is_deleted = FALSE AND mbid = %s",
                (mbid,))

    response = Response(
        json.dumps({
            "mbid": mbid,
            "mappings": [row[0] for row in cur.fetchall()],
        }),
        mimetype="application/json"
    )
    response.headers["Access-Control-Allow-Origin"] = "*"
    return response


@app.route("/mapping-jsonp/<mbid>")
def mapping_jsonp(mbid):
    if not validate_uuid(mbid):
        raise BadRequest("Incorrect MBID (UUID).")

    conn = psycopg2.connect(config.PG_CONNECT)
    cur = conn.cursor()

    cur.execute("SELECT mbid, spotify_uri "
                "FROM mapping "
                "WHERE is_deleted = FALSE AND mbid = %s",
                (mbid,))
    if not cur.rowcount:
        return jsonify({})
    # TODO: Return all mappings to a specified MBID (don't forget to update userscript).
    row = cur.fetchone()
    return jsonify({mbid: row[1]})


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8080)
