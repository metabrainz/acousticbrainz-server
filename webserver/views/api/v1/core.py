from __future__ import absolute_import

import json

from flask import Blueprint, request, jsonify

import db.data
import webserver.views.api.exceptions
from db.data import submit_low_level_data, count_lowlevel
from db.exceptions import NoDataFoundException, BadDataException
from webserver.decorators import crossdomain

import logging
import uuid

bp_core = Blueprint('api_v1_core', __name__)

@bp_core.route("/<uuid:mbid>/count", methods=["GET"])
@crossdomain()
def count(mbid):
    """Get number of low-level data submissions for a recording with a
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
    """Get low-level data for recording with a given MBID.

    This endpoint returns one document at a time. If there are more submissions
    for an MBID, you can browse through them by specifying an offset parameter
    ``n``. Documents are sorted by their submission time.

    You can get total number of low-level submissions using ``/<mbid>/count``
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

    This endpoint returns one document at a time. If there are more submissions
    for an MBID, you can browse through them by specifying an offset parameter
    ``n``. Documents are sorted by submission time of low-level data associated
    with them.

    You can get total number of low-level submissions using ``/<mbid>/count``
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

@bp_core.route("/low-level", methods=["POST"])
def submit_low_level_nombid():
    """Submit low-level data to AcousticBrainz without MBID

    :reqheader Content-Type: *application/json*

    :resheader Content-Type: *application/json*
    """
    raw_data = request.get_data()
    try:
        data = json.loads(raw_data.decode("utf-8"))
    except ValueError as e:
        raise webserver.views.api.exceptions.APIBadRequest("Cannot parse JSON document: %s" % e)
    
    if 'musicbrainz_recordingid' in data['metadata']['tags'].keys():
        mbid = data['metadata']['tags']['musicbrainz_recordingid']
    elif 'musicbrainz_trackid' in data['metadata']['tags'].keys():
        mbid = data['metadata']['tags']['musicbrainz_trackid']
    elif 'md5_encoded' in data['metadata']['audio_properties'].keys():
        md5encoded = data['metadata']['audio_properties']['md5_encoded']
        mbid = db.data.find_md5_duplicates(md5encoded)
        if mbid is not None:
            action = "md5_duplicate"
            return jsonify({"status": "OK", "itemuuid": mbid, "action": action})
        else:
            mbid = str(uuid.uuid4())
            data['metadata']['tags']['musicbrainz_trackid'] = [mbid]
            action = "uuidV4_generate"
    else:
        raise webserver.views.api.exceptions.APIBadRequest('### Bad data format: no mbid nor md5!')
    
    # TODO - add the generated MBID to the data dictionary before submitting
    if mbid is not None:
        try:
            submit_low_level_data(mbid, data)
        except BadDataException as e:
            logging.warn(str(e))
            raise webserver.views.api.exceptions.APIBadRequest("%s" % e)
        status = "OK"
            
    outputmsg = {"status": status, "itemuuid": mbid, "action": action}
    return jsonify(outputmsg)
