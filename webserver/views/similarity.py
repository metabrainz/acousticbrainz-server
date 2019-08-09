from __future__ import absolute_import
from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from flask_login import current_user
from werkzeug.exceptions import NotFound, BadRequest

from webserver import forms
from webserver.views.data import _get_recording_info, _get_youtube_query
from similarity.index_model import AnnoyModel
import db.similarity
import db.data

similarity_bp = Blueprint("similarity", __name__)


@similarity_bp.route("/<uuid:mbid>")
def metrics(mbid):
    offset = request.args.get("n")
    # Can make this a utility?
    if offset:
        try:
            offset = int(offset)
        except ValueError:
            offset = 0
    else:
        offset = 0
    id = db.data.get_lowlevel_id(mbid, offset)
    ref_metadata = _get_extended_info(mbid, offset, id)
    metrics_map = db.similarity.get_all_metrics()
    row_width = 12 / len(metrics_map)

    return render_template(
        'similarity/metrics.html',
        ref_metadata=ref_metadata,
        metrics=metrics_map,
        col_width=row_width
    )


@similarity_bp.route("/<uuid:mbid>/<string:metric>")
def get_similar(mbid, metric):
    offset = request.args.get("n")
    # Can make this a utility?
    if offset:
        try:
            offset = int(offset)
        except ValueError:
            offset = 0
    else:
        offset = 0

    category, metric, description = db.similarity.get_metric_info(metric)
    n_similar = 10

    query_id = db.data.get_lowlevel_id(mbid, offset)
    ref_metadata = _get_extended_info(mbid, offset, query_id)

    try:
        index = AnnoyModel(metric, load_existing=True)
        result_ids, similar_recordings, distances = index.get_nns_by_mbid(mbid, offset, n_similar)
    except (db.exceptions.NoDataFoundException, similarity.exceptions.ItemNotFoundException, similarity.exceptions.IndexNotFoundException), e:
        flash("We're sorry, this index is not currently available for this recording: {}".format(repr(e)))
        return redirect(url_for("similarity.metrics", mbid=mbid, n=offset))

    # If it doesn't exist already, submit to eval_results
    params = (metric, index.n_trees, index.distance_type)
    eval_id = db.similarity.submit_eval_results(query_id, result_ids, distances, params)

    metadata = [_get_extended_info(rec[0], rec[1], id, eval_id=eval_id) for rec, id in zip(similar_recordings, result_ids)]

    form = forms.SimilarityEvaluationForm()
    eval_data = zip(form.eval_list, metadata)

    return render_template(
        "similarity/similar.html",
        metric=metric,
        ref_metadata=ref_metadata,
        metadata=metadata,
        category=category,
        description=description,
        form=form,
        eval_data=eval_data
    )


@similarity_bp.route("/<uuid:mbid>/<string:metric>/eval", methods=['POST'])
def rate_similar(mbid, metric):
    offset = request.args.get("n")
    form = request.json["form"]
    metadata = request.json["metadata"]
    # Can make this a utility?
    if offset:
        try:
            offset = int(offset)
        except ValueError:
            offset = 0
    else:
        offset = 0

    form = forms.SimilarityEvaluationForm()
    # eval_data = zip(form.eval_list, metadata)

    if form.validate_on_submit():
        user_id = current_user.id if current_user.is_authenticated else None
        for eval, rec_metadata in zip(form.eval_list.entries, metadata):
            if eval.data['feedback']:
                # Eval occurred for this recording, create evaluation
                rating = eval.data['feedback']
                suggestion = eval.data['suggestion'] if eval.data['suggestion'] else None
                print(suggestion)
                flash(eval.data['feedback'])
                flash(suggestion)
                result_id = rec_metadata['id']
                eval_id = rec_metadata['eval_id']
                flash(result_rec)
                db.similarity.add_evaluation(user_id, eval_id, result_id, rating, suggestion)
        return jsonify({'success': True}), 200
    return jsonify(form.errors)


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
