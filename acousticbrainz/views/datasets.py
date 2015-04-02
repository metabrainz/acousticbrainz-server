from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from werkzeug.exceptions import NotFound, BadRequest
from acousticbrainz.data import dataset, user as user_data
from jsonschema import ValidationError, validate as validate_json

datasets_bp = Blueprint('datasets', __name__)


@datasets_bp.route('/<uuid:id>/')
def details(id):
    ds = dataset.get(id)
    if not ds:
        raise NotFound("Can't find this dataset.")
    return render_template('datasets/view.html', dataset=ds,
                           author=user_data.get(ds['author']))


@datasets_bp.route('/<uuid:id>/json')
def view_json(id):
    ds = dataset.get(id)
    if not ds:
        raise NotFound("Can't find this dataset.")
    return jsonify(ds)


@datasets_bp.route('/create', methods=('GET', 'POST'))
@login_required
def create():
    if request.method == 'POST':
        dataset_dict = request.get_json()
        if not dataset_dict:
            return jsonify(
                success=False,
                error="Data must be submitted in JSON format.",
            ), 400

        try:
            validate_json(dataset_dict, dataset.DATASET_JSON_SCHEMA)
        except ValidationError as e:
            return jsonify(
                success=False,
                error=str(e),
            ), 400

        dataset_id, error = dataset.create_from_dict(dataset_dict, current_user.id)
        if dataset_id is None:
            return jsonify(
                success=False,
                error=str(error),
            ), 400

        return jsonify(
            success=True,
            dataset_id=dataset_id,
        )
    return render_template('datasets/editor.html', mode="create")


@datasets_bp.route('/<uuid:id>/edit', methods=('GET', 'POST'))
@login_required
def edit(id):
    ds = dataset.get(id)
    if not ds:
        raise NotFound("Can't find this dataset.")

    if ds['author'] is not None and ds['author'] != current_user.id:
        raise BadRequest("You can't edit this dataset.")

    if request.method == 'POST':
        dataset_dict = request.get_json()
        if not dataset_dict:
            return jsonify(
                success=False,
                error="Data must be submitted in JSON format.",
            ), 400

        try:
            validate_json(dataset_dict, dataset.DATASET_JSON_SCHEMA)
        except ValidationError as e:
            return jsonify(
                success=False,
                error=str(e),
            ), 400

        dataset_id, error = dataset.update(id, dataset_dict, current_user.id)
        if dataset_id is None:
            return jsonify(
                success=False,
                error=str(error),
            ), 400

        return jsonify(
            success=True,
            dataset_id=dataset_id,
        )

    return render_template('datasets/editor.html', mode="edit", dataset_id=str(id))


@datasets_bp.route('/<uuid:id>/delete', methods=('GET', 'POST'))
@login_required
def delete(id):
    ds = dataset.get(id)
    if not ds:
        raise NotFound("Can't find this dataset.")
    # TODO: Check if author is deleting.
    # TODO: Show confirmation page and delete if POSTed.
    raise NotImplementedError
