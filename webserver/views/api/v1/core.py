from __future__ import absolute_import

import json

from flask import Blueprint, request, jsonify

import db.data
import webserver.views.api.exceptions
from db.data import submit_low_level_data, count_lowlevel
from db.exceptions import NoDataFoundException, BadDataException
from webserver.decorators import crossdomain
from webserver.external import messybrainz

import logging
import uuid

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

@bp_core.route("/low-level-nombid", methods=["POST"])
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
    
    if 'musicbrainz_recordingid' in data['metadata']['tags'].keys() or 'musicbrainz_trackid' in data['metadata']['tags'].keys():
        raise webserver.views.api.exceptions.APIBadRequest('### The data files contains an ID this endopoint only accept nonmbid submissions!')
    elif 'md5_encoded' in data['metadata']['audio_properties'].keys():
        md5encoded = data['metadata']['audio_properties']['md5_encoded']
        mbid = db.data.find_md5_duplicates(md5encoded)
        if mbid is not None:
            action = "md5_duplicate"
            outputmsg = {"status": "OK", "itemuuid": mbid, "action": action}
            return jsonify(outputmsg), 200
        else:
            if 'artist' in data['metadata']['tags'].keys() and 'title' in data['metadata']['tags'].keys():
                artist = data['metadata']['tags']['artist']
                if isinstance(artist, list):
                    artist = artist[0]
                title = data['metadata']['tags']['title']
                if isinstance(title, list):
                    title = title[0]
                artist_data = {'artist': artist, 'title': title}
                gid, id_type = messybrainz.get_messybrainz_id(artist_data)
                # [TODO] pass the id_type to the submit_low_level (once merged with
                if gid is not None:
                    action = "messybrainz_id"
                    try:
                        data['metadata']['tags']['musicbrainz_trackid'] = [gid]
                        submit_low_level_data(gid, data)
                    except BadDataException as e:
                        logging.warn(str(e))
                        raise webserver.views.api.exceptions.APIBadRequest("%s" % e)
                    status = "OK"
                    outputmsg = {"status": status, "itemuuid": gid, "action": action}
                    return jsonify(outputmsg), 201
                else:
                    # this should refer to an exeption for external data not local data
                    raise NoDataFoundException
            else:
                raise BadDataException

    else:
        raise webserver.views.api.exceptions.APIBadRequest('### Bad data format: no mbid nor md5!')
