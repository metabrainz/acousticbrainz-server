from __future__ import absolute_import

import json
import uuid

from flask import Blueprint, request, jsonify

import db.data
from webserver.utils import validate_offset
import webserver.views.api.exceptions
from db.data import submit_low_level_data, count_lowlevel
from db.exceptions import NoDataFoundException, BadDataException
from webserver.decorators import crossdomain
from utils.container_utils import remove_duplicates
from brainzutils.ratelimit import ratelimit

bp_core = Blueprint('api_v1_core', __name__)


# If this value is increased, ensure that it still fits within the uwsgi header size:
# https://uwsgi-docs.readthedocs.io/en/latest/ThingsToKnow.html
# > By default uWSGI allocates a very small buffer (4096 bytes) for the headers of each request.
# > If you start receiving "invalid request block size" in your logs, it could mean you need a bigger buffer.
# > Increase it (up to 65535) with the buffer-size option.

#: The maximum number of items that you can pass as a recording_ids parameter to bulk lookup endpoints
MAX_ITEMS_PER_BULK_REQUEST = 25

# Individual features selectable in get_many_individual_features.
# Note: metadata.version and metadata.audio_properties will be included in all responses.
AVAILABLE_FEATURES = {
    "lowlevel.average_loudness": ["llj.data->'lowlevel'->'average_loudness'", None],
    "lowlevel.dynamic_complexity": ["llj.data->'lowlevel'->'dynamic_complexity'", None],
    "metadata.audio_properties.replay_gain": ["llj.data->'metadata'->'audio_properties'->'replay_gain'", None],
    "metadata.tags": ["llj.data->'metadata'->'tags'", {}],
    "rhythm.beats_count": ["llj.data->'rhythm'->'beats_count'", None],
    "rhythm.beats_loudness.mean": ["llj.data->'rhythm'->'beats_loudness'->'mean'", None],
    "rhythm.bpm": ["llj.data->'rhythm'->'bpm'", None],
    "rhythm.bpm_histogram_first_peak_bpm.mean": ["llj.data->'rhythm'->bpm_histogram_first_peak_bpm'->'mean'", None],
    "rhythm.bpm_histogram_second_peak_bpm.mean": ["llj.data->'rhythm'->bpm_histogram_second_peak_bpm'->'mean'", None],
    "rhythm.danceability": ["llj.data->'rhythm'->'danceability'", None],
    "rhythm.onset_rate": ["llj.data->'rhythm'->'onset_rate'", None],
    "tonal.chords_key": ["llj.data->'tonal'->'chords_key'", None],
    "tonal.chords_scale": ["llj.data->'tonal'->'chords_scale'", None],
    "tonal.key_key": ["llj.data->'tonal'->'key_key'", None],
    "tonal.key_scale": ["llj.data->'tonal'->'key_scale'", None],
    "tonal.key_strength": ["llj.data->'tonal'->'key_strength'", None],
    "tonal.tuning_frequency": ["llj.data->'tonal'->'tuning_frequency'", None],
    "tonal.tuning_equal_tempered_deviation": ["llj.data->'tonal'->'tuning_equal_tempered_deviation'", None]
}

#: Features that can be selected individually from the bulk low-level endpoint
LOWLEVEL_INDIVIDUAL_FEATURES = sorted(list(AVAILABLE_FEATURES.keys()))


@bp_core.route("/<uuid(strict=False):mbid>/count", methods=["GET"])
@crossdomain()
@ratelimit()
def count(mbid):
    """Get the number of low-level data submissions for a recording with a
    given MBID.

    **Example response**:

    .. sourcecode:: json

        {
            "mbid": mbid,
            "count": n
        }

    MBID values are always lower-case, even if the provided recording MBID is upper-case or mixed case.

    :resheader Content-Type: *application/json*
    """
    return jsonify({
        'mbid': mbid,
        'count': count_lowlevel(str(mbid)),
    })


@bp_core.route("/<uuid(strict=False):mbid>/low-level", methods=["GET"])
@crossdomain()
@ratelimit()
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
    offset = request.args.get("n")
    _, mbid, offset = _validate_arguments(str(mbid), offset)
    try:
        return jsonify(db.data.load_low_level(mbid, offset))
    except NoDataFoundException:
        raise webserver.views.api.exceptions.APINotFound("Not found")


@bp_core.route("/<uuid(strict=False):mbid>/high-level", methods=["GET"])
@crossdomain()
@ratelimit()
def get_high_level(mbid):
    """Get high-level data for recording with a given MBID.

    This endpoint returns one document at a time. If there are many submissions
    for an MBID, you can browse through them by specifying an offset parameter
    ``n``. Documents are sorted by the submission time of their associated
    low-level documents.

    You can get the total number of low-level submissions using ``/<mbid>/count``
    endpoint.

    :query n: *Optional.* Integer specifying an offset for a document.
    :query map_classes: *Optional.* If set to 'true', map class names to human-readable values
    TODO: provide a link to what these mappings are

    :resheader Content-Type: *application/json*
    """
    offset = request.args.get("n")
    _, mbid, offset = _validate_arguments(str(mbid), offset)
    map_classes = _validate_map_classes(request.args.get("map_classes"))
    try:
        return jsonify(db.data.load_high_level(mbid, offset, map_classes))
    except NoDataFoundException:
        raise webserver.views.api.exceptions.APINotFound("Not found")


@bp_core.route("/<uuid:mbid>/low-level", methods=["POST"])
@ratelimit()
def submit_low_level(mbid):
    """Submit low-level data to AcousticBrainz.

    :reqheader Content-Type: *application/json*

    :resheader Content-Type: *application/json*
    """
    # The uuid argument matcher in this method is set to strict mode, which means
    # that we only accept uuids in lower-case
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


def _validate_map_classes(map_classes):
    """Validate the map_classes parameter

    Arguments:
        map_classes (Optional[str]): the value of the query parameter

    Returns:
        (bool): True if the map_classes parameter is 'true', False otherwise"""

    return map_classes is not None and map_classes.lower() == 'true'


def _generate_normalised_mbid_mapping(query_arguments):
    """
    :param query_arguments: a list of tuples (mbid, parsed_mbid, offset) as returned by _validate_arguments
    :return: a dictionary mapping {mbid: parsed_mbid} only if
    """
    mapping = {}
    for mbid, parsed_mbid, _ in query_arguments:
        if mbid != parsed_mbid:
            mapping[mbid] = parsed_mbid
    return mapping


def _validate_arguments(mbid, offset):
    """Validate the mbid and offset.

    If the offset is None, return 0, otherwise interpret it as a number. If it is
    not a number, return 0. Don't allow negative numbers.

    If the mbid is an invalid UUID, raise an APIBadRequest
    If the mbid isn't normalised (all lower-case, with hyphens), normalise it.

    Returns:
        a tuple (original_mbid, normalised_mbid, offset)
    """
    try:
        normalised_mbid = str(uuid.UUID(mbid))
    except ValueError:
        # an invalid uuid is 404
        raise webserver.views.api.exceptions.APIBadRequest("'%s' is not a valid UUID" % mbid)

    if offset:
        try:
            offset = int(offset)
            # Don't allow negative offsets
            offset = max(offset, 0)
        except ValueError:
            offset = 0
    else:
        offset = 0

    return mbid, normalised_mbid, offset


def _parse_bulk_params(params):
    """Validate and parse a bulk query parameter string.

    A valid parameter string takes the form
      mbid[:offset];mbid[:offset];...
    Where offset is a number >=0. Offsets are optional.
    mbid must be a UUID.

    If an offset is not specified non-numeric, or negativeit is replaced with 0.
    If an mbid is not valid, an APIBadRequest Exception is
    raised listing the bad MBID and no further processing is done.

    The mbid is normalised to all lower-case, with hyphens between sections.

    Returns a list of tuples (mbid, parsed_mbid, offset).
    mbid is the mbid as passed by the client. parsed_mbid is a normalised version of this mbid
    (all lower-case with hyphens in the correct places).
    """

    ret = []

    for recording in params.split(";"):
        parts = str(recording).split(":")
        mbid = parts[0]
        if len(parts) == 1:
            offset = None
        elif len(parts) == 2:
            offset = parts[1]
        else:
            raise webserver.views.api.exceptions.APIBadRequest("More than 1 colon (:) in '%s'" % recording)

        args = _validate_arguments(mbid, offset)
        ret.append(args)

    # Remove duplicates, preserving order
    return remove_duplicates(ret)


def _get_recording_ids_from_request():
    """
    Read the ?recording_ids query parameter from the flask request and validate it.
    The parameter should be in the format
        mbid:n;mbid:n
    where mbid is a recording MBID and n is an optional integer offset. If the offset is
    missing or non-integer, it is replaced with 0

    Returns:
        a list of (mbid, offset) tuples representing the parsed query string.

    Raises:
        APIBadRequest if there is no recording_ids parameter, there are more than 25 MBIDs in the parameter,
        or the format of the mbids or offsets are invalid
    """
    recording_ids = request.args.get("recording_ids")

    if not recording_ids:
        raise webserver.views.api.exceptions.APIBadRequest("Missing `recording_ids` parameter")

    recordings = _parse_bulk_params(recording_ids)
    if len(recordings) > MAX_ITEMS_PER_BULK_REQUEST:
        raise webserver.views.api.exceptions.APIBadRequest("More than %s recordings not allowed per request" % MAX_ITEMS_PER_BULK_REQUEST)

    return recordings


@bp_core.route("/low-level", methods=["GET"])
@crossdomain()
@ratelimit()
def get_many_lowlevel():
    """Get low-level data for many recordings at once.

    **Example response**:

    .. sourcecode:: json

       {"mbid1": {"offset1": {document},
                  "offset2": {document}},
        "mbid2": {"offset1": {document}},
        "mbid_mapping": {"MBID1": "mbid1"}
       }

    MBIDs and offset keys are returned as strings (as per JSON encoding rules).
    If an offset is not specified in the request for an MBID or is not a valid integer >=0,
    the offset will be 0.

    MBID keys are always returned in a
    `normalised form <https://en.wikipedia.org/wiki/Universally_unique_identifier#Format>`_,
    even if the provided recording MBIDs are not given in this form. In the case that a requested MBID is not given
    in this normalised form, the value `mbid_mapping` in the response will be a dictionary that maps user-provided MBIDs
    to this form.

    If the list of MBIDs in the query string has a recording which is not
    present in the database, then it is silently ignored and will not appear
    in the returned data.

    If you only need a specific feature and don't want to download the whole low-level document, you can request
    specific features using the ``features`` parameter. The shape of the returned document will be the same as
    a full low-level document, and will contain only the specified features as well as the ``metadata.audio_properties``
    and ``metadata.version`` objects.

    :query recording_ids: *Required.* A list of recording MBIDs to retrieve

      Takes the form `mbid[:offset];mbid[:offset]`. Offsets are optional, and should
      be >= 0

      You can specify up to :py:const:`~webserver.views.api.v1.core.MAX_ITEMS_PER_BULK_REQUEST` MBIDs in a request.

    :query features: *Optional.* A list of features to be returned for each mbid.

      Takes the form `feature1;feature2`.

      You can specify the following features in a request: :py:const:`~webserver.views.api.v1.core.LOWLEVEL_INDIVIDUAL_FEATURES`.

    :resheader Content-Type: *application/json*
    """
    recordings = _get_recording_ids_from_request()
    mbid_mapping = _generate_normalised_mbid_mapping(recordings)
    # The result from check_bad_request is (mbid, good_mbid, offset)
    recordings = [(mbid, offset) for _, mbid, offset in recordings]

    parsed_features = _parse_individual_features()
    if parsed_features:
        recording_details = db.data.load_many_individual_features(recordings, parsed_features)
    else:
        recording_details = db.data.load_many_low_level(recordings)

    recording_details['mbid_mapping'] = {}
    if mbid_mapping:
        recording_details['mbid_mapping'] = mbid_mapping

    return jsonify(recording_details)


@bp_core.route("/high-level", methods=["GET"])
@crossdomain()
@ratelimit()
def get_many_highlevel():
    """Get high-level data for many recordings at once.

    **Example response**:

    .. sourcecode:: json

       {"mbid1": {"offset1": {document},
                  "offset2": {document}},
        "mbid2": {"offset1": {document}},
        "mbid_mapping": {"MBID1": "mbid1"}
       }

    MBIDs and offset keys are returned as strings (as per JSON encoding rules).
    If an offset is not specified in the request for an mbid or is not a valid integer >=0,
    the offset will be 0.

    MBID keys are always returned in a normalised form (all lower-case, separated in groups of 8-4-4-4-12 characters),
    even if the provided recording MBIDs are not given in this form. In the case that a requested MBID is not given
    in this normalised form, the value `mbid_mapping` in the response will be a dictionary mapping user-provided MBIDs
    to this form.

    If the list of MBIDs in the query string has a recording which is not
    present in the database, then it is silently ignored and will not appear
    in the returned data.

    :query recording_ids: *Required.* A list of recording MBIDs to retrieve

      Takes the form `mbid[:offset];mbid[:offset]`. Offsets are optional, and should
      be >= 0

      You can specify up to :py:const:`~webserver.views.api.v1.core.MAX_ITEMS_PER_BULK_REQUEST` MBIDs in a request.

    :query map_classes: *Optional.* If set to 'true', map class names to human-readable values

    :resheader Content-Type: *application/json*
    """
    map_classes = _validate_map_classes(request.args.get("map_classes"))
    recordings = _get_recording_ids_from_request()
    mbid_mapping = _generate_normalised_mbid_mapping(recordings)
    # The result from check_bad_request is (mbid, good_mbid, offset)
    recordings = [(mbid, offset) for _, mbid, offset in recordings]
    recording_details = db.data.load_many_high_level(recordings, map_classes)
    recording_details['mbid_mapping'] = {}
    if mbid_mapping:
        recording_details['mbid_mapping'] = mbid_mapping

    return jsonify(recording_details)


def _parse_individual_features():
    """Check whether the features are found or not.
    Parse the query string of features to create a list of
    the json paths to features, excluding those that are
    not offered.

    If features are missing, an APIBadRequest Exception is
    raised stating the missing features message.

    Returns:
        parsed_features, a list of tuples of the form:
            (<feature_path>, <alias>, <default_type>)

            <feature_path> is a string holding the path to a feature:
            "llj.data->feature_name"

            <alias> is a string alias for a feature:
            "lowlevel.feature_name"

            <default_type> is the type to which a feature value will default
            if it is non-existent, depending on the alias from
            :py:const:`~webserver.views.api.v1.core.AVAILABLE_FEATURES`
    """
    features_param = request.args.get("features")
    if not features_param:
        return None

    parsed_features = []
    for alias in features_param.split(';'):
        if alias in AVAILABLE_FEATURES:
            default_type = AVAILABLE_FEATURES[alias][1]
            feature_path = AVAILABLE_FEATURES[alias][0]
            parsed_features.append((feature_path, alias, default_type))

    # Always include metadata.version and metadata.audio_properties
    metadata_version = "llj.data->'metadata'->'version'"
    metadata_version_alias = "metadata.version"
    metadata_audio_properties = "llj.data->'metadata'->'audio_properties'"
    metadata_audio_properties_alias = "metadata.audio_properties"

    parsed_features.append((metadata_version, metadata_version_alias, {}))
    parsed_features.append((metadata_audio_properties, metadata_audio_properties_alias, {}))

    # Remove duplicates, preserving order
    ret = []
    return [x for x in parsed_features if not (x in ret or ret.append(x))]


@bp_core.route("/count", methods=["GET"])
@crossdomain()
@ratelimit()
def get_many_count():
    """Get low-level count for many recordings at once. MBIDs not found in
    the database are omitted in the response.

    **Example response**:

    .. sourcecode:: json

       {"mbid1": {"count": 3},
        "mbid2": {"count": 1},
        "mbid_mapping": {"MBID1": "mbid1"}
       }

    MBID keys are always returned in a normalised form (all lower-case, separated in groups of 8-4-4-4-12 characters),
    even if the provided recording MBIDs are not given in this form. In the case that a requested MBID is not given
    in this normalised form, the value `mbid_mapping` in the response will be a dictionary mapping user-provided MBIDs
    to this form.

    :query recording_ids: *Required.* A list of recording MBIDs to retrieve

      Takes the form `mbid;mbid`.

    You can specify up to :py:const:`~webserver.views.api.v1.core.MAX_ITEMS_PER_BULK_REQUEST` MBIDs in a request.

    :resheader Content-Type: *application/json*
    """
    recordings = _get_recording_ids_from_request()
    mbid_mapping = _generate_normalised_mbid_mapping(recordings)
    # The result from check_bad_request is (mbid, good_mbid, offset)
    mbids = [mbid for (_, mbid, offset) in recordings]
    recording_counts = db.data.count_many_lowlevel(mbids)
    recording_counts['mbid_mapping'] = {}
    if mbid_mapping:
        recording_counts['mbid_mapping'] = mbid_mapping

    return jsonify(recording_counts)
