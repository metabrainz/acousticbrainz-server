from __future__ import absolute_import
from flask import Blueprint, request, jsonify
from db.data import submit_low_level_data, count_lowlevel
import db.data
from db.exceptions import NoDataFoundException, BadDataException
from webserver.decorators import crossdomain
import webserver.exceptions
import json

bp_core = Blueprint('api_v1_core', __name__)


@bp_core.route("/<uuid:mbid>/count", methods=["GET"])
@crossdomain()
def count(mbid):
    """Endpoint for getting number of submissions for a given recording."""
    return jsonify({
        'mbid': mbid,
        'count': count_lowlevel(str(mbid)),
    })


@bp_core.route("/<uuid:mbid>/low-level", methods=["GET"])
@crossdomain()
def get_low_level(mbid):
    """Endpoint for fetching low-level data.

    If there is more than one document with the same mbid, you can specify
    an offset as a query parameter in the form of ?n=x, where x is an integer
    starting from 0
    """
    offset = _validate_offset(request.args.get("n"))
    try:
        return jsonify(db.data.load_low_level(str(mbid), offset))
    except NoDataFoundException:
        raise webserver.exceptions.APINotFound("Not found")


@bp_core.route("/<uuid:mbid>/high-level", methods=["GET"])
@crossdomain()
def get_high_level(mbid):
    """Endpoint for fetching high-level data.

    If there is more than one document with the same mbid, you can specify
    an offset as a query parameter in the form of ?n=x, where x is an integer
    starting from 0
    """
    offset = _validate_offset(request.args.get("n"))
    try:
        return jsonify(db.data.load_high_level(str(mbid), offset))
    except NoDataFoundException:
        raise webserver.exceptions.APINotFound("Not found")


@bp_core.route("/<uuid:mbid>/low-level", methods=["POST"])
def submit_low_level(mbid):
    """Endpoint for submitting low-level information to AcousticBrainz."""
    raw_data = request.get_data()
    try:
        data = json.loads(raw_data.decode("utf-8"))
    except ValueError as e:
        raise webserver.exceptions.APIBadRequest("Cannot parse JSON document: %s" % e)

    try:
        submit_low_level_data(str(mbid), data)
    except BadDataException as e:
        raise webserver.exceptions.APIBadRequest("%s" % e)
    return jsonify({"message": "ok"})


def _validate_offset(offset):
    """Validate the offset.

    If the offset is None, return 0, otherwise interpret it as a number. If it is
    not a number, raise 400.
    """
    if offset:
        try:
            offset = int(offset)
        except ValueError:
            raise webserver.exceptions.APIBadRequest("Offset must be an integer value")
    else:
        offset = 0
    return offset
