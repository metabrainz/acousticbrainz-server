from __future__ import absolute_import
from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from flask_login import current_user, login_required
from werkzeug.exceptions import NotFound, BadRequest

from webserver import forms
from webserver.utils import validate_offset
from webserver.decorators import auth_required
from webserver.views.data import _get_recording_info, _get_youtube_query
from similarity.index_model import AnnoyModel
import similarity.exceptions
import db.similarity
import db.data
import db.exceptions

similarity_bp = Blueprint("similarity", __name__)


@similarity_bp.route("/<uuid:mbid>")
def metrics(mbid):
    offset = validate_offset(request.args.get("n"))
    metrics_map = db.similarity.get_all_metrics()
    row_width = 12 / len(metrics_map)

    try:
        id = db.data.get_lowlevel_id(mbid, offset)
        ref_metadata = _get_extended_info(mbid, offset, id)
        return render_template(
            'similarity/metrics.html',
            ref_metadata=ref_metadata,
            metrics=metrics_map,
            col_width=row_width
        )
    except db.exceptions.NoDataFoundException:
        raise NotFound


@similarity_bp.route("/<uuid:mbid>/<string:metric>")
@login_required
def get_similar(mbid, metric):
    offset = validate_offset(request.args.get("n"))

    try:
        category, metric, description = db.similarity.get_metric_info(metric)
        query_id = db.data.get_lowlevel_id(mbid, offset)
        ref_metadata = _get_extended_info(mbid, offset, query_id)
        return render_template(
            "similarity/eval.html",
            metric=metric,
            description=description,
            ref_metadata=ref_metadata,
        )
    except (db.exceptions.NoDataFoundException, NotFound) as e:
        raise NotFound(e)


@similarity_bp.route("/service/<uuid:mbid>/<string:metric>")
@auth_required
def get_similar_service(mbid, metric):
    """Get similar recordings in terms of the specified metric
    to the specified (MBID, offset) combination. Each item in
    the list returned holds metadata for a similar recording.
    """
    offset = validate_offset(request.args.get("n"))
    n_similar = 10
    try:
        query_id = db.data.get_lowlevel_id(mbid, offset)
        category, metric, description = db.similarity.get_metric_info(metric)
        # Annoy model currently uses default parameters
        index = AnnoyModel(metric, load_existing=True)
        result_ids, similar_recordings, distances = index.get_nns_by_mbid(mbid, offset, n_similar)
    except (db.exceptions.NoDataFoundException, similarity.exceptions.ItemNotFoundException, similarity.exceptions.IndexNotFoundException), e:
        flash("We're sorry, this index is not currently available for this recording: {}".format(repr(e)))
        return redirect(url_for("similarity.metrics", mbid=mbid, n=offset))

    # If it doesn't exist already, submit to eval_results
    params = (metric, index.n_trees, index.distance_type)
    eval_id = db.similarity.submit_eval_results(query_id, result_ids, distances, params)
    # Check if current user has already submitted this eval form
    user_id = current_user.id
    submitted = db.similarity.check_for_eval_submission(user_id, eval_id)

    metadata = [_get_extended_info(rec[0], rec[1], id, eval_id=eval_id) for rec, id in zip(similar_recordings, result_ids)]
    metric = {"category": category, "description": description}

    ret = {"metadata": metadata, "metric": metric, "submitted": submitted}
    return jsonify(ret)
    

@similarity_bp.route("/service/<uuid:mbid>/<string:metric>/evaluate", methods=['POST'])
@auth_required
def add_evaluations(mbid, metric):
    offset = validate_offset(request.args.get("n"))

    form = request.json["form"]
    if not form:
        return jsonify({
            'success': False,
            'error': "Request does not contain form data."
        }), 400

    metadata = request.json["metadata"]
    if not metadata:
        return jsonify({
            'success': False,
            'error': "Request does not contain metadata for similar recordings."
        }), 400

    user_id = current_user.id if current_user.is_authenticated else None
    for rec in metadata:
        # *NOTE*: result_id is the lowlevel.id of one similar recording in metadata, and
        # eval_id is eval_results.id that identifies an evaluationi query for similar recordings.
        eval_id = rec['eval_id']
        result_id = rec['lowlevel_id']
        eval = form[str(result_id)]
        if not eval['feedback'] and not eval['suggestion']:
            # Eval did not occur for this recording
            continue
        else:
            # Eval occurred for this recording, create evaluation
            rating = eval['feedback'] if eval['feedback'] else None
            suggestion = eval['suggestion'] if eval['suggestion'] else None
            db.similarity.add_evaluation(user_id, eval_id, result_id, rating, suggestion)

    return jsonify({'success': True}), 200


def _get_extended_info(mbid, offset, id, eval_id=None):
    info = _get_recording_info(mbid, None)
    if not info:
        raise NotFound('No info for the recording {}'.format(mbid))
    info['mbid'] = mbid
    info['submission_offset'] = offset
    info['youtube_query'] = _get_youtube_query(info)
    info['lowlevel_id'] = id
    if eval_id:
        info['eval_id'] = eval_id
    return info
