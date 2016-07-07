from __future__ import absolute_import

import json
import sys

from flask import Blueprint, request, jsonify

import db.data
import db.dataset_eval
import webserver.views.api.exceptions
from db.data import submit_low_level_data, count_lowlevel
from db.exceptions import NoDataFoundException, BadDataException
from webserver.decorators import crossdomain

bp_core = Blueprint('api_v1_core', __name__)


@bp_core.route("/<uuid:mbid>/count", methods=["GET"])
@crossdomain()
def count(mbid):
    """Get the number of low-level data submissions for a recording with a
    given MBID.

    :resheader Content-Type: *application/json*
    """
    return jsonify({
        'mbid': mbid,
        'count': count_lowlevel(str(mbid)),
    })


@bp_core.route("/<uuid:mbid>/low-level", methods=["GET"])
@crossdomain()
def get_low_level(mbid):
    """Get low-level data for a recording with a given MBID.

    This endpoint returns one document at a time. If there are many submissions
    for an MBID, you can browse through them by specifying an offset parameter
    ``n``. Documents are sorted by their submission time.

    You can the get total number of low-level submissions using the ``/<mbid>/count``
    endpoint.

    :query n: *Optional.* Integer specifying an offset for a document.

    :resheader Content-Type: *application/json*
    """
    offset = _validate_offset(request.args.get("n"))
    try:
        return jsonify(db.data.load_low_level(str(mbid), offset))
    except NoDataFoundException:
        raise webserver.views.api.exceptions.APINotFound("Not found")


@bp_core.route("/<uuid:mbid>/high-level", methods=["GET"])
@crossdomain()
def get_high_level(mbid):
    """Get high-level data for recording with a given MBID.

    This endpoint returns one document at a time. If there are many submissions
    for an MBID, you can browse through them by specifying an offset parameter
    ``n``. Documents are sorted by the submission time of their associated
    low-level documents.

    You can get the total number of low-level submissions using ``/<mbid>/count``
    endpoint.

    :query n: *Optional.* Integer specifying an offset for a document.

    :resheader Content-Type: *application/json*
    """
    offset = _validate_offset(request.args.get("n"))
    try:
        return jsonify(db.data.load_high_level(str(mbid), offset))
    except NoDataFoundException:
        raise webserver.views.api.exceptions.APINotFound("Not found")


@bp_core.route("/<uuid:mbid>/low-level", methods=["POST"])
def submit_low_level(mbid):
    """Submit low-level data to AcousticBrainz.

    :reqheader Content-Type: *application/json*

    :resheader Content-Type: *application/json*
    """
    raw_data = request.get_data()
    try:
        data = json.loads(raw_data.decode("utf-8"))
    except ValueError as e:
        raise webserver.views.api.exceptions.APIBadRequest("Cannot parse JSON document: %s" % e)

    try:
        submit_low_level_data(str(mbid), data)
    except BadDataException as e:
        raise webserver.views.api.exceptions.APIBadRequest("%s" % e)
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
            raise webserver.views.api.exceptions.APIBadRequest("Offset must be an integer value")
    else:
        offset = 0
    return offset

@bp_core.route("/<user_api_key>/get_pending_jobs", methods=["GET"])
def get_pending_jobs(user_api_key):
    """ Return the pending jobs for a user.

    Retrieve the Job Ids for the pending jobs for the user whose
    user id is given as an argument and return that.
    """
    final_result = {}
    try:
        pending_jobs = db.dataset_eval.get_user_pending_jobs(user_api_key)
        for i in range(len(pending_jobs)):
            final_result[i+1] = str(pending_jobs[i][0])
    except:
        e = sys.exc_info()[0]
        raise webserver.exceptions.APIBadRequest("%s" % e)
    return jsonify(final_result)
