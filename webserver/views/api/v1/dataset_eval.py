from __future__ import absolute_import
from flask import Blueprint, jsonify, request
from flask_login import current_user
from webserver.decorators import auth_required
from webserver.views.api import exceptions
import db.dataset_eval

bp_dataset_eval = Blueprint('api_v1_dataset_eval', __name__)

@bp_dataset_eval.route("/jobs", methods=["GET"])
@auth_required
def get_jobs():
    """Return a list of jobs related to the current user.
       Identify the current user by being logged in or by passing a Token for authentication.

       :query status: *Required.* Status of jobs to be returned. Possible values: "pending"
       :query location: *Required.* Location that the user wants to evaluate jobs. Possible values: "remote"

       **Example Response**:

       .. sourcecode:: json

       {
           'username': 'Test'
           'jobs': [
               {
                   'dataset_name': 'test_dataset',
                   'created': 'Wed, 08 Jun 2016 21:41:58 GMT',
                   'job_id': '0fc553b6-f3a8-4e24-af39-56ac02276ed9'
               }
           ]
       }

    :reqheader Content-Type: *application/json*
    :<json string username:  MusicBrainz username of the user.
    :<json array jobs:       Jobs which match the query.
    """

    location = request.args.get("location")
    status = request.args.get("status")
    # TODO: This endpoint can be used in the future to get any type of job,
    #       but for now we only use it for pending/remote.
    if location != db.dataset_eval.EVAL_REMOTE or status != db.dataset_eval.STATUS_PENDING:
        raise exceptions.APIBadRequest("parameter location must be 'remote' and status 'pending'")

    jobs = db.dataset_eval.get_remote_pending_jobs_for_user(current_user.id)
    return jsonify(
        username=current_user.musicbrainz_id,
        jobs=jobs
    )


