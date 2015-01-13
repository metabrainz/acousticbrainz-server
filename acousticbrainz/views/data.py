from flask import Blueprint, request, Response, render_template, redirect
from acousticbrainz.data import load_low_level, load_high_level, get_summary_data, submit_low_level_data
from werkzeug.exceptions import BadRequest
from urllib import quote_plus
import json

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
    raw_data = request.get_data()
    try:
        data = json.loads(raw_data)
    except ValueError, e:
        raise BadRequest("Cannot parse JSON document: %s" % e)

    submit_low_level_data(mbid, data)
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
    lowlevel, highlevel, genres, moods, other = get_summary_data(mbid)

    # Tomahawk player stuff
    if not ('artist' in lowlevel['metadata']['tags'] and 'title' in lowlevel['metadata']['tags']):
        tomahawk_url = None
    else:
        tomahawk_url = "http://toma.hk/embed.php?artist={artist}&title={title}".format(
            artist=quote_plus(lowlevel['metadata']['tags']['artist'][0].encode("UTF-8")),
            title=quote_plus(lowlevel['metadata']['tags']['title'][0].encode("UTF-8")))

    return render_template("summary.html", lowlevel=lowlevel, highlevel=highlevel, mbid=mbid,
                           genres=genres, moods=moods, other=other, tomahawk_url=tomahawk_url)
