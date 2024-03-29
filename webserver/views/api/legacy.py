from flask import Blueprint, request, jsonify, current_app
from brainzutils.ratelimit import ratelimit
from db.data import count_lowlevel, submit_low_level_data
from db.exceptions import NoDataFoundException, BadDataException
from webserver.decorators import crossdomain
from webserver.views.api import exceptions
import db.data
import json
import uuid

api_legacy_bp = Blueprint('api', __name__)


@api_legacy_bp.route("/<uuid(strict=False):mbid>/count", methods=["GET"])
@crossdomain()
@ratelimit()
def count(mbid):
    mbid, offset = _validate_data_arguments(str(mbid), None)
    return jsonify({
        'mbid': mbid,
        'count': count_lowlevel(mbid),
    })


@api_legacy_bp.route("/<string:mbid>/low-level", methods=["GET"])
@crossdomain()
@ratelimit()
def get_low_level(mbid):
    """Endpoint for fetching low-level data.
    If there is more than one document with the same mbid, you can specify
    an offset as a query parameter in the form of ?n=x, where x is an integer
    starting from 0
    """
    mbid, offset = _validate_data_arguments(mbid, request.args.get("n"))
    try:
        return jsonify(db.data.load_low_level(mbid, offset))
    except NoDataFoundException:
        raise exceptions.APINotFound("Not found")


@api_legacy_bp.route("/<string:mbid>/high-level", methods=["GET"])
@crossdomain()
@ratelimit()
def get_high_level(mbid):
    """Endpoint for fetching high-level data.
    If there is more than one document with the same mbid, you can specify
    an offset as a query parameter in the form of ?n=x, where x is an integer
    starting from 0
    """
    mbid, offset = _validate_data_arguments(mbid, request.args.get("n"))
    try:
        return jsonify(db.data.load_high_level(mbid, offset))
    except NoDataFoundException:
        raise exceptions.APINotFound("Not found")


@api_legacy_bp.route("/<uuid:mbid>/low-level", methods=["POST"])
def submit_low_level(mbid):
    """Endpoint for submitting low-level information to AcousticBrainz."""
    raw_data = request.get_data()
    try:
        data = json.loads(raw_data.decode("utf-8"))
    except ValueError as e:
        raise exceptions.APIBadRequest("Cannot parse JSON document: %s" % e)

    max_duplicate_submissions = current_app.config.get('MAX_NUMBER_DUPLICATE_SUBMISSIONS', None)

    try:
        submit_low_level_data(mbid, data, 'mbid', max_duplicate_submissions)
    except BadDataException as e:
        raise exceptions.APIBadRequest("%s" % e)
    return jsonify({"message": "ok"})


def _validate_data_arguments(mbid, offset):
    """Validate the mbid and offset. If the mbid is not a valid uuid, raise 404.
    If the offset is None, return 0, otherwise interpret it as a number. If it is
    not a number, raise 400."""
    try:
        mbid = str(uuid.UUID(mbid))
    except ValueError:
        # an invalid uuid is 404
        raise exceptions.APINotFound("Not found")

    if offset:
        try:
            offset = int(offset)
        except ValueError:
            raise exceptions.APIBadRequest("Offset must be an integer value")
    else:
        offset = 0

    return mbid, offset
