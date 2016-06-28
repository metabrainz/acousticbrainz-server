from __future__ import absolute_import
from flask import Blueprint, jsonify, request
from flask_login import current_user
from webserver.decorators import auth_required
from webserver.views.api import exceptions as api_exceptions
import db.dataset
import db.exceptions
from utils import dataset_validator

bp_datasets = Blueprint('api_v1_datasets', __name__)


@bp_datasets.route("/<uuid:dataset_id>", methods=["GET"])
def get_dataset(dataset_id):
    """Retrieve a dataset.

    :resheader Content-Type: *application/json*
    """
    return jsonify(get_check_dataset(dataset_id))


@bp_datasets.route("/", methods=["POST"])
@auth_required
def create_dataset():
    """Create a new dataset.

    **Example request**:

    .. sourcecode:: json

        {
            "name": "Mood",
            "description": "Dataset for mood classification.",
            "public": true,
            "classes": [
                {
                    "name": "Happy",
                    "description": "Recordings that represent happiness.",
                    "recordings": ["770cc467-8dde-4d22-bc4c-a42f91e"]
                },
                {
                    "name": "Sad"
                }
            ]
        }

    :reqheader Content-Type: *application/json*
    :<json string name: *Required.* Name of the dataset.
    :<json string description: *Optional.* Description of the dataset.
    :<json boolean public: *Optional.* ``true`` to make dataset public, ``false`` to make it private. New datasets are
        public by default.
    :<json array classes: *Optional.* Array of objects containing information about classes to add into new dataset. For
        example:

        .. sourcecode:: json

            {
                "name": "Happy",
                "description": "Recordings that represent happiness.",
                "recordings": ["770cc467-8dde-4d22-bc4c-a42f91e"]
            }


    :resheader Content-Type: *application/json*
    :>json boolean success: ``True`` on successful creation.
    :>json string dataset_id: ID (UUID) of newly created dataset.
    """
    dataset_dict = request.get_json()
    if not dataset_dict:
        raise api_exceptions.APIBadRequest("Data must be submitted in JSON format.")
    if "public" not in dataset_dict:
        dataset_dict["public"] = True
    if "classes" not in dataset_dict:
        dataset_dict["classes"] = []
    try:
        dataset_id = db.dataset.create_from_dict(dataset_dict, current_user.id)
    except dataset_validator.ValidationException as e:
        raise api_exceptions.APIBadRequest(e.message)

    return jsonify(
        success=True,
        dataset_id=dataset_id,
    )


@bp_datasets.route("/<uuid:dataset_id>", methods=["DELETE"])
@auth_required
def delete_dataset(dataset_id):
    """Delete a dataset."""
    ds = get_dataset(dataset_id)
    if ds["author"] != current_user.id:
        raise api_exceptions.APIUnauthorized("You can't delete this dataset.")
    db.dataset.delete(ds["id"])
    return jsonify(
        success=True,
        message="Dataset has been deleted."
    )


@bp_datasets.route("/<uuid:dataset_id>", methods=["PUT"])
@auth_required
def update_dataset_details(dataset_id):
    """Update dataset details.

    If one of the fields is not specified, it will not be updated.

    **Example request**:

    .. sourcecode:: json

        {
            "name": "Not Mood",
            "description": "Dataset for mood misclassification.",
            "public": true
        }

    :reqheader Content-Type: *application/json*
    :<json string name: *Optional.* Name of the dataset.
    :<json string description: *Optional.* Description of the dataset.
    :<json boolean public: *Optional.* ``True`` to make dataset public, ``false`` to make it private.

    :resheader Content-Type: *application/json*
    """
    raise NotImplementedError


@bp_datasets.route("/<uuid:dataset_id>/classes", methods=["POST"])
@auth_required
def add_class(dataset_id):
    """Add class into a dataset.

    **Example request**:

    .. sourcecode:: json

        {
            "name": "Not Mood",
            "description": "Dataset for mood misclassification.",
        }

    :reqheader Content-Type: *application/json*
    :<json string name: *Required.* Name of the class. Must be unique within a dataset.
    :<json string description: *Optional.* Description of the class.
    :<json array public: *Optional.* Array of recording MBIDs (``string``) to add into that class. For example:
        ``["770cc467-8dde-4d22-bc4c-a42f91e"]``.


    :resheader Content-Type: *application/json*
    """
    raise NotImplementedError


@bp_datasets.route("/<uuid:dataset_id>/classes", methods=["PUT"])
@auth_required
def update_class(dataset_id):
    """Update class in a dataset.

    If one of the fields is not specified, it will not be updated.

    **Example request**:

    .. sourcecode:: json

        {
            "name": "Very happy",
            "new_name": "Recordings that represent ultimate happiness."
        }

    :reqheader Content-Type: *application/json*
    :<json string name: *Required.* Current name of the class.
    :<json string new_name: *Optional.* New name of the class. Must be unique within a dataset.
    :<json string description: *Optional.* Description of the class.

    :resheader Content-Type: *application/json*
    """
    raise NotImplementedError


@bp_datasets.route("/<uuid:dataset_id>/classes", methods=["DELETE"])
@auth_required
def delete_class(dataset_id):
    """Delete class from a dataset.

    **Example request**:

    .. sourcecode:: json

        {
            "name": "Sad"
        }

    :reqheader Content-Type: *application/json*
    :<json string name: *Required.* Name of the class.

    :resheader Content-Type: *application/json*
    """
    raise NotImplementedError


@bp_datasets.route("/<uuid:dataset_id>/recordings", methods=["PUT"])
@auth_required
def add_recordings(dataset_id):
    """Add recordings to a class in a dataset.

    **Example request**:

    .. sourcecode:: json

        {
            "class_name": "Happy",
            "recordings": ["770cc467-8dde-4d22-bc4c-a42f91e"]
        }

    :reqheader Content-Type: *application/json*
    :<json string class_name: *Required.* Name of the class.
    :<json array recordings: *Required.* Array of recoding MBIDs (``string``) to add into that class.

    :resheader Content-Type: *application/json*
    """
    raise NotImplementedError


@bp_datasets.route("/<uuid:dataset_id>/recordings", methods=["DELETE"])
@auth_required
def delete_recordings(dataset_id):
    """Delete recordings from a class in a dataset.

    **Example request**:

    .. sourcecode:: json

        {
            "class_name": "Happy",
            "recordings": ["770cc467-8dde-4d22-bc4c-a42f91e"]
        }

    :reqheader Content-Type: *application/json*
    :<json string class_name: *Required.* Name of the class.
    :<json array recordings: *Required.* Array of recoding MBIDs (``string``) that need be deleted from a class.

    :resheader Content-Type: *application/json*
    """
    raise NotImplementedError


def get_check_dataset(dataset_id):
    """Wrapper for `dataset.get` function in `db` package. Meant for use with the API.

    Checks the following conditions and raises NotFound exception if they
    aren't met:
    * Specified dataset exists.
    * Current user is allowed to access this dataset.
    """
    try:
        ds = db.dataset.get(dataset_id)
    except db.exceptions.NoDataFoundException as e:
        raise api_exceptions.APINotFound("Can't find this dataset.")
    if ds["public"] or (current_user.is_authenticated and
                        ds["author"] == current_user.id):
        return ds
    else:
        raise api_exceptions.APINotFound("Can't find this dataset.")
