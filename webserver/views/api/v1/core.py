from __future__ import absolute_import

import json
import uuid

from flask import Blueprint, request, jsonify

import db.data
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
        submit_low_level_data(str(mbid), data, 'mbid')
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


def _parse_bulk_params(params):
    """Validate and parse a bulk query parameter string.

    A valid parameter string takes the form
      mbid[:offset];mbid[:offset];...
    Where offset is a number >=0. Offsets are optional.
    mbid must be a UUID.

    If an offset is not specified or is invalid, 0 is used as a default.
    If an mbid is not valid, an APIBadRequest Exception is
    raised listing the bad MBID and no further processing is done.

    Returns a list of tuples (mbid, offset)
    """

    ret = []

    for recording in params.split(";"):
        parts = str(recording).split(":")
        recording_id = parts[0]
        try:
            uuid.UUID(recording_id)
        except ValueError:
            raise webserver.views.api.exceptions.APIBadRequest("'%s' is not a valid UUID" % recording_id)
        if len(parts) > 2:
            raise webserver.views.api.exceptions.APIBadRequest("More than 1 : in '%s'" % recording)
        elif len(parts) == 2:
            try:
                offset = int(parts[1])
                # Don't allow negative offsets
                offset = max(offset, 0)
            except ValueError:
                offset = 0
        else:
            offset = 0

        ret.append((recording_id, offset))

    # Remove duplicates, preserving order
    seen = set()
    return [x for x in ret if not (x in seen or seen.add(x))]


def check_bad_request_for_multiple_recordings():
    """Check whether the recording ids are not more than 200 
    and whether the recording ids are found or not.

    If recording_ids are missing, an APIBadRequest Exception is
    raised stating the missing MBIDs message.
    If there are more than 200 recordings, then an APIBadRequest Exception is raised.
    In both cases, no further processing is done.
    """
    recording_ids = request.args.get("recording_ids")

    if not recording_ids:
        raise webserver.views.api.exceptions.APIBadRequest("Missing `recording_ids` parameter")

    recordings = _parse_bulk_params(recording_ids)
    if len(recordings) > 200:
        raise webserver.views.api.exceptions.APIBadRequest("More than 200 recordings not allowed per request")

    return recordings

# DELETE THIS
# def get_data_for_multiple_recordings(collect_data):
#     """Gets low-level and high-level data using the function collect_data
#     """
#     recordings = check_bad_request_for_multiple_recordings()

#     recording_details = {}

#     for recording_id, offset in recordings:
#         try:
#             recording_details.setdefault(recording_id, {})[offset] = collect_data(recording_id, offset)
#         except NoDataFoundException:
#             pass

#     return jsonify(recording_details)


@bp_core.route("/low-level", methods=["GET"])
@crossdomain()
def get_many_lowlevel():
    """Get low-level data for many recordings at once.

    **Example response**:

    .. sourcecode:: json

       {"mbid1": {"offset1": {document},
                  "offset2": {document}},
        "mbid2": {"offset1": {document}}
       }

    Offset keys are returned as strings, as per JSON encoding rules.
    If an offset was not specified in the request for an mbid, the offset
    will be 0.

    If the list of MBIDs in the query string has a recording which is not
    present in the database, then it is silently ignored and will not appear
    in the returned data.

    :query recording_ids: *Required.* A list of recording MBIDs to retrieve

      Takes the form `mbid[:offset];mbid[:offset]`. Offsets are optional, and should
      be >= 0

    :resheader Content-Type: *application/json*
    """
    recordings = check_bad_request_for_multiple_recordings()
    recording_details = db.data.load_many_low_level(recordings)

    return jsonify(recording_details)


@bp_core.route("/high-level", methods=["GET"])
@crossdomain()
def get_many_highlevel():
    """Get high-level data for many recordings at once.
    
    **Example response**:

    .. sourcecode:: json

       {"mbid1": {"offset1": {document},
                  "offset2": {document}},
        "mbid2": {"offset1": {document}}
       }

    Offset keys are returned as strings, as per JSON encoding rules.
    If an offset was not specified in the request for an mbid, the offset
    will be 0.

    If the list of MBIDs in the query string has a recording which is not
    present in the database, then it is silently ignored and will not appear
    in the returned data.

    :query recording_ids: *Required.* A list of recording MBIDs to retrieve

      Takes the form `mbid[:offset];mbid[:offset]`. Offsets are optional, and should
      be >= 0

    :resheader Content-Type: *application/json*
    """
    recordings = check_bad_request_for_multiple_recordings()
    recording_details = db.data.load_many_high_level(recordings)
    
    return jsonify(recording_details)


@bp_core.route("/count", methods=["GET"])
@crossdomain()
def get_many_count():
    """Get low-level count for many recordings at once. MBIDs not found in
    the database are omitted in the response.

    **Example response**:

    .. sourcecode:: json

       {"mbid1": {"count": 3},
        "mbid2": {"count": 1}
       }

    :query recording_ids: *Required.* A list of recording MBIDs to retrieve

      Takes the form `mbid;mbid`.

    :resheader Content-Type: *application/json*
    """
    recordings = check_bad_request_for_multiple_recordings()

    mbids = [mbid for (mbid, offset) in recordings]
    return jsonify(db.data.count_many_lowlevel(mbids))
