from __future__ import absolute_import
from flask import Blueprint, jsonify, request
from flask_login import current_user
from webserver.decorators import auth_required
import db.dataset_eval

bp_dataset_eval = Blueprint('api_v1_dataset_eval', __name__)

@bp_dataset_eval.route("/pending-jobs", methods=["GET"])
@auth_required
def pending_jobs():
    """Return a list of pending jobs for a user to be evaluated remotely.
       API key argument is required.

       **Example Response**:

       .. sourcecode:: json

       {
           'success': True,
           'username': 'Test'
           'jobs': [
               {
                   'dataset_name': 'test_dataset',
                   'job_created': 'Wed, 08 Jun 2016 21:41:58 GMT',
                   'job_id': '0fc553b6-f3a8-4e24-af39-56ac02276ed9'
               }
           ]
       }

    :reqheader Content-Type: *application/json*
    :<json boolean success: *Required.* Status of the query.
    :<json string username: *Required.* Metabrainz username of the user.
    :<json array jobs: *Required.* Array of objects containing information about jobs which are pending
        and are to be evaluated remotely.
    """
    job_details = db.dataset_eval.get_remote_pending_jobs_for_user(current_user.id)
    return jsonify(
        success=True,
        username=job_details['username'],
        jobs=job_details['jobs']
    )

