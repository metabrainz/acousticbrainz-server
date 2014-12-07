from flask import Blueprint, request, Response, render_template, redirect, current_app
from acousticbrainz.data import load_low_level, load_high_level
from acousticbrainz.utils import sanity_check_json, clean_metadata, interpret_high_level
from werkzeug.exceptions import BadRequest, ServiceUnavailable, InternalServerError
from hashlib import sha256
from urllib import quote_plus
import psycopg2
import json
import time

data_bp = Blueprint('data', __name__)


@data_bp.route("/api")
def api():
    return redirect("/data")


@data_bp.route("/data")
def data():
    return render_template("data.html")


@data_bp.route("/<uuid:mbid>/low-level", methods=["POST"])
def submit_low_level(mbid):
    """Endpoint for submitting low-level information to AcousticBrainz."""
    mbid = str(mbid)
    raw_data = request.get_data()
    try:
        data = json.loads(raw_data)
    except ValueError, e:
        raise BadRequest("Cannot parse JSON document: %s" % e)

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

    return ""


@data_bp.route("/<uuid:mbid>/low-level/view", methods=["GET"])
def view_low_level(mbid):
    data = json.dumps(json.loads(load_low_level(mbid)), indent=4, sort_keys=True)
    return render_template("json-display.html", title="Low-level JSON for %s" % mbid, data=data)


@data_bp.route("/<uuid:mbid>/low-level", methods=["GET"])
def get_low_level(mbid):
    """Endpoint for fetching low-level information to AcousticBrainz."""
    return Response(load_low_level(mbid), content_type='application/json')


@data_bp.route("/<uuid:mbid>/high-level/view", methods=["GET"])
def view_high_level(mbid):
    data = json.dumps(json.loads(load_high_level(mbid)), indent=4, sort_keys=True)
    return render_template("json-display.html", title="High-level JSON for %s" % mbid, data=data)


@data_bp.route("/<uuid:mbid>/high-level", methods=["GET"])
def get_high_level(mbid):
    """Endpoint for fetching high-level information to AcousticBrainz."""
    return Response(load_high_level(mbid), content_type='application/json')


@data_bp.route("/<uuid:mbid>", methods=["GET"])
def get_summary(mbid):
    mbid = str(mbid)
    conn = psycopg2.connect(current_app.config['PG_CONNECT'])
    cur = conn.cursor()
    try:
        cur.execute("SELECT data FROM lowlevel WHERE mbid = %s", (mbid, ))
        if not cur.rowcount:
            return render_template("summary.html", mbid="")

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

        # Tomahawk player stuff
        if not ('artist' in lowlevel['metadata']['tags'] and 'title' in lowlevel['metadata']['tags']):
            tomahawk_url = None
        else:
            tomahawk_url = "http://toma.hk/embed.php?artist={artist}&title={title}".format(
                artist=quote_plus(lowlevel['metadata']['tags']['artist'][0].encode("UTF-8")),
                title=quote_plus(lowlevel['metadata']['tags']['title'][0].encode("UTF-8")))

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

        return render_template("summary.html", lowlevel=lowlevel, highlevel=highlevel, mbid=mbid,
                               genres=genres, moods=moods, other=other, tomahawk_url=tomahawk_url)

    except psycopg2.IntegrityError, e:
        raise BadRequest(str(e))
    except psycopg2.OperationalError, e:
        raise ServiceUnavailable(str(e))

    return InternalServerError("whoops!")
