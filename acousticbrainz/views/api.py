from flask import Blueprint, request, Response
from acousticbrainz.data import load_low_level, load_high_level, submit_low_level_data
from werkzeug.exceptions import BadRequest
import json

api_bp = Blueprint('api', __name__)


@api_bp.route("/<uuid:mbid>/low-level", methods=["GET"])
def get_low_level(mbid):
    """Endpoint for fetching low-level information to AcousticBrainz."""
    return Response(load_low_level(mbid), content_type='application/json')


@api_bp.route("/<uuid:mbid>/high-level", methods=["GET"])
def get_high_level(mbid):
    """Endpoint for fetching high-level information to AcousticBrainz."""
    return Response(load_high_level(mbid), content_type='application/json')


@api_bp.route("/<uuid:mbid>/low-level", methods=["POST"])
def submit_low_level(mbid):
    """Endpoint for submitting low-level information to AcousticBrainz."""
    raw_data = request.get_data()
    try:
        data = json.loads(raw_data)
    except ValueError, e:
        raise BadRequest("Cannot parse JSON document: %s" % e)

    submit_low_level_data(mbid, data)
    return ""
