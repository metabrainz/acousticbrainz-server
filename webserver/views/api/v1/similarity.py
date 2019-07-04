from __future__ import absolute_import

from flask import Blueprint, jsonify, request

import webserver.views.api.exceptions
from webserver.decorators import crossdomain
from webserver.views.api.v1.core import _validate_offset, _parse_bulk_params, check_bad_request_for_multiple_recordings
import similarity.utils
from similarity.index_model import BASE_INDICES
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
    **NOTE** This parameter will currently default to angular. We need to decide with evaluation which distance measure is most appropriate.
    :query distance_type: *Optional.* String determining the distance
        formula that an index will use when computing similarity.
        Default is angular.
        This parameter will no longer exist when we have developed a set
        list of index specifications that we will use.
    :query n_trees: *Optional.* Integer determines the number of trees
        in the index that is used to compute similarity.
        Default is 10 trees.
        This parameter will no longer exist when we have developed a set
        list of index specifications that we will use.
    :query n_neighbours *Optional.* Integer determines the number of
        similar recordings that should be returned.
        Default is 200 recordings.
    :query metric: *Required.* String specifying the metric name to be
        used when finding the most similar recordings.
        The metrics available are shown here :py:const:`~similarity.metrics.BASE_METRICS`.
    :resheader Content-Type: *application/json*
    """
    offset = _validate_offset(request.args.get("n"))
    metric, distance_type, n_trees, n_neighbours = _check_index_params(metric)
    try:
        index = similarity.utils.load_index_model(metric, distance_type, n_trees)
    except IndexNotFoundException:
        raise webserver.views.api.exceptions.APIBadRequest("Index does not exist with specified parameters.")

    try:
        similar_recordings = index.get_nns_by_mbid(mbid, offset, n_neighbours)
        return jsonify(similar_recordings)
    except ItemNotFoundException:
        raise webserver.views.api.exceptions.APIBadRequest("The item of interest is not indexed.")


def _check_index_params(metric):
    if not metric:
        raise webserver.views.api.exceptions.APIBadRequest("Missing `metric` parameter.")
    if metric not in BASE_INDICES:
        raise webserver.views.api.exceptions.APIBadRequest("An index with the specified metric does not exist.")

    distance_type = request.args.get("distance_type")
    if not distance_type:
        distance_type = "angular"
    else:
        if distance_type not in BASE_INDICES[metric]:
            raise webserver.views.api.exceptions.APIBadRequest("An index for metric {} does not exist with the specified distance type.".format(metric))

    n_trees = request.args.get("n_trees")
    if not n_trees:
        n_trees = 10
    else:
        if n_trees not in BASE_INDICES[metric][distance_type]:
            raise webserver.views.api.exceptions.APIBadRequest("An index for metric `{}` with distance type `{}` does not exist with the specified number of trees.".format(metric, distance_type))

    n_neighbours = request.args.get("n_neighbours")
    if not n_neighbours or n_neighbours > 1000:
        n_neighbours = 200
    else:
        try:
            n_neighbours = int(n_neighbours)
        except ValueError:
            raise webserver.views.api.exceptions.APIBadRequest("Number of neighbours must be an integer value.")

    return metric, distance_type, n_trees, n_neighbours


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


    **NOTE** This parameter will currently default to angular. We need to decide with evaluation which distance measure is most appropriate.
    :query distance_type: *Optional.* String determining the distance
        formula that an index will use when computing similarity.
        Default is angular.
        This parameter will no longer exist when we have developed a set
        list of index specifications that we will use.

    :query n_trees: *Optional.* Integer determines the number of trees
        in the index that is used to compute similarity.
        Default is 10 trees.
        This parameter will no longer exist when we have developed a set
        list of index specifications that we will use.

    :query n_neighbours *Optional.* Integer determines the number of
        similar recordings that should be returned.
        Default is 200 recordings.

    :query metric: *Required.* String specifying the metric name to be
        used when finding the most similar recordings.
        The metrics available are shown here :py:const:`~similarity.metrics.BASE_METRICS`.

    :query recording_ids: *Required.* A list of recording MBIDs to retrieve

      Takes the form `mbid[:offset];mbid[:offset]`. Offsets are optional, and should
      be >= 0

    :resheader Content-Type: *application/json*
    """
    recordings = check_bad_request_for_multiple_recordings()
    metric, distance_type, n_trees, n_neighbours = _check_index_params(metric)
    try:
        index = similarity.utils.load_index_model(metric, distance_type, n_trees)
    except IndexNotFoundException:
        raise webserver.views.api.exceptions.APIBadRequest("Index does not exist with specified parameters.")

    similar_recordings = index.get_bulk_nns_by_mbid(recordings, n_neighbours)
    return jsonify(similar_recordings)


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
    if len(recordings) > 2:
        raise webserver.views.api.exceptions.APIBadRequest("More than 2 recordings \
            not allowed in request")

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

    **NOTE** This parameter will currently default to angular. We need to decide with evaluation which distance measure is most appropriate.
    :query distance_type: *Optional.* String determining the distance
        formula that an index will use when computing similarity.
        Default is angular.
        This parameter will no longer exist when we have developed a set
        list of index specifications that we will use.

    :query n_trees: *Optional.* Integer determines the number of trees
        in the index that is used to compute similarity.
        Default is 10 trees.
        This parameter will no longer exist when we have developed a set
        list of index specifications that we will use.

    :resheader Content-Type: *application/json*
    """
    rec_one, rec_two = check_bad_request_between_recordings()
    distance_type, n_trees, n_neighbours = _check_index_params(metric)
    try:
        index = similarity.utils.load_index_model(metric, distance_type, n_trees)
    except IndexNotFoundException:
        raise webserver.views.api.exceptions.APIBadRequest("Index does not exist with specified parameters.")

    try:
        distance = index.get_similarity_between(rec_one, rec_two)
        return {metric: distance}
    except (NoDataFoundException, ItemNotFoundException):
        return {}


















