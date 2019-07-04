from __future__ import absolute_import
from flask import Blueprint, jsonify, request
from flask_login import current_user
from webserver.decorators import auth_required
from webserver.views.api import exceptions
import db.dataset_eval
import db.dataset
from webserver.views.api.v1 import datasets

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

@bp_dataset_eval.route("/jobs/<uuid:job_id>", methods=["GET"])
@auth_required
def job_details(job_id):
    """Returns the details of a particular job.
       API key argument is required.

       **Example Response**:

       .. sourcecode:: json

       {
           "created": "Tue, 07 Jun 2016 22:12:32 GMT",
           "dataset": {
               "author": 1,
               "classes": [
                   {
                       "description": null,
                       "id": "141",
                       "name": "Class2",
                       "recordings": [
                           "d08ab44b-94c8-482b-a67f-a683a30fbe5a",
                           "2618cb1d-8699-49df-93f7-a8afea6c914f"
                       ]
                   },
                   {
                       "description": null,
                       "id": "142",
                       "name": "Class1",
                       "recordings": [
                           "5251c17c-c161-4e73-8b1c-4231e8e39095",
                           "c0dccd50-f9dc-476c-b1f1-84f00adeab51"
                       ]
                   }
               ],
               "created": "Mon, 02 May 2016 16:41:08 GMT",
               "description": "",
               "id": "5375e0ff-a6d0-44a3-bee1-05d46fbe6bd5",
               "last_edited": "Mon, 02 May 2016 16:41:08 GMT",
               "name": "test4",
               "public": true
           },
           "dataset_id": "5375e0ff-a6d0-44a3-bee1-05d46fbe6bd5",
           "eval_location": "local",
           "id": "7804abe5-58be-4c9c-a787-22b91d031489",
           "options": {
               "filter_type": null,
               "normalize": false
           },
           "result": null,
           "snapshot_id": "2d51df50-6b71-410e-bf9a-7e877fc9c6c0",
           "status": "pending",
           "status_msg": null,
           "testing_snapshot": null,
           "training_snapshot": null,
           "updated": "Tue, 07 Jun 2016 22:12:32 GMT"
    }
    """
    job = db.dataset_eval.get_job(job_id)
    if not job:
        raise exceptions.APINotFound('No such job')

    job['dataset'] = datasets.get_check_dataset(job['dataset_id'])
    return jsonify(job)
