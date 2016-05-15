from __future__ import absolute_import

import json

from flask import Blueprint, request, jsonify

import webserver.views.api.exceptions
from db.data import submit_low_level_data
from db.exceptions import BadDataException

api_legacy_bp = Blueprint('api_legacy', __name__)


@api_legacy_bp.route("/<uuid:mbid>/low-level", methods=["POST"])
def submit_low_level(mbid):
    """Endpoint for submitting low-level information to AcousticBrainz."""
    raw_data = request.get_data()
    try:
        data = json.loads(raw_data.decode("utf-8"))
    except ValueError as e:
        raise webserver.views.api.exceptions.APIBadRequest("Cannot parse JSON document: %s" % e)

    try:
        submit_low_level_data(mbid, data)
    except BadDataException as e:
        raise webserver.views.api.exceptions.APIBadRequest("%s" % e)
    return jsonify({"message": "ok"})
