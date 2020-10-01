from __future__ import absolute_import

import collections
from operator import itemgetter

from flask import Blueprint, jsonify, request

import webserver.views.api.exceptions
from webserver.utils import validate_offset
from webserver.decorators import crossdomain
from webserver.views.api.v1.core import _parse_bulk_params, _get_recording_ids_from_request
from similarity.index_model import BASE_INDICES, AnnoyModel
from similarity.exceptions import IndexNotFoundException, ItemNotFoundException
from db.exceptions import NoDataFoundException

bp_similarity = Blueprint('api_v1_similarity', __name__)


@bp_similarity.route("/<metric>/<uuid(strict=False):mbid>", methods=["GET"])
@crossdomain()
def get_similar_recordings(metric, mbid):
    """Get the most similar submissions to an (MBID, offset) combination.
    If there are many submissions for an MBID, one can be specified
    with an offset parameter ``n``. Documents are sorted by their
    submission time.
    You can the get total number of low-level submissions using the ``/<mbid>/count``
    endpoint.

    **Example response**:
    .. sourcecode:: json
        {"mbid": {"offset": [(most_similar_mbid, offset),
                                ...,
                            (least_similar_mbid, offset)]
                 }
        }

    :query n: *Optional.* Integer specifying an offset for a document.
        The first submission has offset n=0. If not specified, this
        submission will be used as the default value.
    :query n_neighbours *Optional.* Integer determines the number of
        similar recordings that should be returned.
        Default is 200 recordings.
    :query threshold: *Optional.* Only return items whose distance from the query recording
        is less than this (0-1). This may result in the number of returned items being less than
        n_neighbours if it is set.
    :query remove_dups: *Optional.* If ``true``, remove duplicate submissions that have the
        same score.  This may result in the number of returned items being less than
        n_neighbours if it is set.
    :query metric: *Required.* String specifying the metric name to be
        used when finding the most similar recordings.
        The metrics available are shown here :py:const:`~similarity.metrics.BASE_METRICS`.

    :resheader Content-Type: *application/json*
    """
    offset = validate_offset(request.args.get("n"))
    metric, distance_type, n_trees, n_neighbours, threshold, remove_dups = _check_index_params(metric)
    try:
        index = AnnoyModel(metric, n_trees=n_trees, distance_type=distance_type, load_existing=True)
    except IndexNotFoundException:
        raise webserver.views.api.exceptions.APIBadRequest("Index does not exist with specified parameters.")

    try:
        recordings = index.get_nns_by_mbid(str(mbid), offset, n_neighbours)
        response = _limit_recordings_by_threshold(recordings, threshold)
        response = _sort_and_remove_duplicate_submissions(response, remove_dups)
        return jsonify(response)

    except NoDataFoundException:
        raise webserver.views.api.exceptions.APIBadRequest("No submission exists for the given (MBID, offset) combination.")
    except ItemNotFoundException:
        raise webserver.views.api.exceptions.APIBadRequest("The submission of interest is not indexed.")


def _limit_recordings_by_threshold(recordings, threshold):
    """Return only recordings whose distance is equal or below a threshold

    Arguments:
        recordings: a list of dictionaries {"recording_mbid": x, "offset": y, "distance": z}
        threshold: the threshold limit to remove recordings
    """
    if threshold is None:
        return recordings
    return [r for r in recordings if r['distance'] <= threshold]


def _sort_and_remove_duplicate_submissions(recordings, remove_dups=False):
    """Sort recordings by distance, recording_mbid, and then offset.
    Optionally remove recordings that have the same distance, even if the offset is different

    Arguments:
        recordings: a list of dictionaries {"recording_mbid": x, "offset": y, "distance": z}
        remove_dups: if True, remove items from recordings if the distance and recording_mbid
                     are the same as the previous item
    """
    recordings = sorted(recordings, key=itemgetter('distance', 'recording_mbid', 'offset'))
    last_distance = None
    last_mbid = None
    result = []
    for recording in recordings:
        distance = recording['distance']
        mbid = recording['recording_mbid']
        if not remove_dups or mbid != last_mbid or distance != last_distance:
            result.append(recording)
        last_distance = distance
        last_mbid = mbid
    return result


def  _check_index_params(metric):
    if metric not in BASE_INDICES:
        raise webserver.views.api.exceptions.APIBadRequest("An index with the specified metric does not exist.")

    distance_type = request.args.get("distance_type")
    if not distance_type or distance_type not in BASE_INDICES[metric]:
        distance_type = "angular"
        # TODO: can we raise an error here that isn't fatal to let the user know that the value is being
        #  defaulted when index doesn't exist?

    n_trees = request.args.get("n_trees")
    if not n_trees or n_trees not in BASE_INDICES[metric][distance_type]:
        n_trees = 10

    n_neighbours = request.args.get("n_neighbours")
    try:
        n_neighbours = int(n_neighbours)
        if n_neighbours < 1:
            n_neighbours = 1
        elif n_neighbours > 1000:
            n_neighbours = 1000
    except (ValueError, TypeError):
        n_neighbours = 200

    threshold = request.args.get("threshold")
    try:
        if threshold:
            threshold = float(threshold)
            if threshold > 1.0:
                threshold = 1.0
            if threshold < 0:
                threshold = 0.0
    except (ValueError, TypeError):
        threshold = None

    remove_dups = request.args.get("remove_dups")
    if remove_dups == "true":
        remove_dups = True
    else:
        remove_dups = False

    return metric, distance_type, n_trees, n_neighbours, threshold, remove_dups


@bp_similarity.route("/<metric>", methods=["GET"])
@crossdomain()
def get_many_similar_recordings(metric):
    """Get the most similar submissions to multiple (MBID, offset) combinations.

    **Example response**:
    .. sourcecode:: json
        {"mbid1": {"offset1": [(most_similar_mbid, offset),
                                ...,
                            (least_similar_mbid, offset)],
                  "offset2": [(most_similar_mbid, offset),
                                ...,
                            (least_similar_mbid, offset)]
                 },
         ...,

         "mbidN": {"offset1": [(most_similar_mbid, offset),
                                ...,
                               (least_similar_mbid, offset)]
                  }
        }

    MBIDs and offset keys are returned as strings (as per JSON encoding rules).
    If an offset is not specified in the request for an mbid or is not a valid integer >=0,
    the offset will be 0.

    If the list of MBIDs in the query string has a recording which is not
    present in the database, then it is silently ignored and will not appear
    in the returned data.

    :query n_neighbours *Optional.* The number of similar recordings that
        should be returned for each item in ``recording_ids`` (1-1000).
        Default is 200 recordings.

    :query metric: *Required.* String specifying the metric name to be
        used when finding the most similar recordings.
        The metrics available are shown here :py:const:`~similarity.metrics.BASE_METRICS`.

    :query recording_ids: *Required.* A list of recording MBIDs to retrieve

      Takes the form `mbid[:offset];mbid[:offset]`. Offsets are optional, and should
      be >= 0

    :query threshold: *Optional.* Only return items whose distance from the query recording
    is less than this (0-1). This may result in the number of returned items being less than
    n_neighbours if it is set.

    :query remove_dups: *Optional.* If ``true``, remove duplicate submissions that have the
    same score.  This may result in the number of returned items being less than
    n_neighbours if it is set.

    :resheader Content-Type: *application/json*
    """
    recordings = _get_recording_ids_from_request()
    recordings = [(mbid, offset) for _, mbid, offset in recordings]
    metric, distance_type, n_trees, n_neighbours, threshold, remove_dups = _check_index_params(metric)
    try:
        index = AnnoyModel(metric, n_trees=n_trees, distance_type=distance_type, load_existing=True)
    except IndexNotFoundException:
        raise webserver.views.api.exceptions.APIBadRequest("Index does not exist with specified parameters.")

    similar_recordings = index.get_bulk_nns_by_mbid(recordings, n_neighbours)
    result = collections.defaultdict(dict)
    for mbid, submissions in similar_recordings.items():
        for offset, items in submissions.items():
            items = _limit_recordings_by_threshold(items, threshold)
            items = _sort_and_remove_duplicate_submissions(items, remove_dups)
            result[mbid][offset] = items
    return jsonify(result)


def check_bad_request_between_recordings():
    """
    Check if a request for similarity between recordings is valid. The ?recording_ids parameter
    to the current flask request is checked to see if it is present and if it follows
    the format
        mbid:n;mbid:n
    where mbid is a recording MBID and n is an optional integer offset. If the offset is
    missing or non-integer, it is replaced with 0

    Returns:
        a two-list of (mbid, offset) tuples representing the parsed query string.

    Raises:
        APIBadRequest if there is no recording_ids parameter, there are more than 2 MBIDs in the parameter,
        or the format of the mbids or offsets are invalid
    """
    recording_ids = request.args.get("recording_ids")

    if not recording_ids:
        raise webserver.views.api.exceptions.APIBadRequest("Missing `recording_ids` parameter")

    recordings = _parse_bulk_params(recording_ids)
    recordings = [(mbid, offset) for _, mbid, offset in recordings]
    if not len(recordings) == 2:
        raise webserver.views.api.exceptions.APIBadRequest("Does not contain 2 recordings in the request")

    return recordings


@bp_similarity.route("/<metric>/between", methods=["GET"])
@crossdomain()
def get_similarity_between(metric):
    """Get the distance measure for similarity between two MBIDs.
    The distance measure will correspond to the index of the
    specified metric.

    The metrics available are shown here :py:const:`~similarity.metrics.BASE_METRICS`.

    **Example response**:
    .. sourcecode:: json
        {"metric": [<distance_vector>]}

    **NOTE** If an (MBID, offset) combination specified does not exist, or is not
    present in the index, an empty dictionary will be returned.

    :query recording_ids: *Required.* A list of the two recordings for which
        similarity should be found between.

        Takes the form `mbid[:offset]:mbid[:offset]`. Offsets are optional, and should
        be integers >= 0

    :resheader Content-Type: *application/json*
    """
    recordings = check_bad_request_between_recordings()
    metric, distance_type, n_trees, n_neighbours, threshold, remove_dups = _check_index_params(metric)
    try:
        index = AnnoyModel(metric, n_trees=n_trees, distance_type=distance_type, load_existing=True)
    except IndexNotFoundException:
        raise webserver.views.api.exceptions.APIBadRequest("Index does not exist with specified parameters.")

    try:
        distance = index.get_similarity_between(recordings[0], recordings[1])
        return jsonify({metric: distance})
    except (NoDataFoundException, ItemNotFoundException):
        return jsonify({})
