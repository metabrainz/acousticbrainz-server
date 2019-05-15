from __future__ import absolute_import
from werkzeug.exceptions import InternalServerError
from webserver.testing import ServerTestCase
from db.testing import TEST_DATA_PATH
import db.exceptions
import db.dataset
import db.dataset_eval
import db.api_key
import webserver.views.api.exceptions
import datetime
from utils import dataset_validator

import json
import mock
import os

class APIDatasetEvaluationViewsTestCase(ServerTestCase):

    def setUp(self):
        super(APIDatasetEvaluationViewsTestCase, self).setUp()

        self.test_user_mb_name = 'tester'
        self.test_user_id = db.user.create(self.test_user_mb_name)
        self.test_user = db.user.get(self.test_user_id)

        self.test_dataset = {
            'author': 1,
            'classes': [
                {
                    'description': 'null',
                    'id': '141',
                    'name': 'Class2',
                    'recordings': [
                        'd08ab44b-94c8-482b-a67f-a683a30fbe5a',
                        '2618cb1d-8699-49df-93f7-a8afea6c914f'
                    ]
                },
                {
                    'description': 'null',
                    'id': '142',
                    'name': 'Class1',
                    'recordings': [
                        '5251c17c-c161-4e73-8b1c-4231e8e39095',
                        'c0dccd50-f9dc-476c-b1f1-84f00adeab51'
                    ]
                 }
            ],
            'created': 'Mon, 02 May 2016 16:41:08 GMT',
            'description': '',
            'id': '5375e0ff-a6d0-44a3-bee1-05d46fbe6bd5',
            'last_edited': 'Mon, 02 May 2016 16:41:08 GMT',
            'name': 'test4',
            'public': True
        }

        self.test_job_details = {
            'created': 'Tue, 07 Jun 2016 22:12:32 GMT',
            'dataset_id': '5375e0ff-a6d0-44a3-bee1-05d46fbe6bd5',
            'eval_location': 'local',
            'id': '7804abe5-58be-4c9c-a787-22b91d031489',
            'options': {
                'filter_type': 'null',
                'normalize': False
            },
            'result': 'null',
            'snapshot_id': '2d51df50-6b71-410e-bf9a-7e877fc9c6c0',
            'status': 'pending',
            'status_msg': 'null',
            'testing_snapshot': 'null',
            'training_snapshot': 'null',
            'updated': 'Tue, 07 Jun 2016 22:12:32 GMT'
        }

    @mock.patch('db.dataset_eval.get_remote_pending_jobs_for_user')
    def test_get_pending_jobs_for_user(self, get_remote_pending_jobs_for_user):
        self.temporary_login(self.test_user_id)

        get_remote_pending_jobs_for_user.return_value = [{
            'job_id': '7804abe5-58be-4c9c-a787-22b91d031489',
            'dataset_name': 'test',
            'job_created': '2016-07-26T18:20:57'
        }]
        resp = self.client.get('/api/v1/datasets/evaluation/jobs?status=pending&location=remote')
        self.assertEqual(resp.status_code, 200)
        get_remote_pending_jobs_for_user.assert_called_once_with(self.test_user_id)

        expected = {
            'jobs': [{
                'job_id': '7804abe5-58be-4c9c-a787-22b91d031489',
                'dataset_name': 'test',
                'job_created': '2016-07-26T18:20:57'
                }],
            'username': 'tester'}
        self.assertEqual(resp.json, expected)

    @mock.patch('db.dataset_eval.get_remote_pending_jobs_for_user')
    def test_get_pending_jobs_not_logged_in(self, get_remote_pending_jobs_for_user):
        """ Check that a user must be logged in """
        resp = self.client.get('/api/v1/datasets/evaluation/jobs?status=pending&location=remote')
        self.assertEqual(resp.status_code, 401)

    @mock.patch('db.dataset_eval.get_remote_pending_jobs_for_user')
    def test_get_pending_jobs_invalid_parameters(self, get_remote_pending_jobs_for_user):
        """ Endpoint requires a valid status and location parameter """
        self.temporary_login(self.test_user_id)

        resp = self.client.get('/api/v1/datasets/evaluation/jobs?status=pending')
        self.assertEqual(resp.status_code, 400)

        resp = self.client.get('/api/v1/datasets/evaluation/jobs?location=remote')
        self.assertEqual(resp.status_code, 400)

        resp = self.client.get('/api/v1/datasets/evaluation/jobs?status=pendin&location=remote')
        self.assertEqual(resp.status_code, 400)

        resp = self.client.get('/api/v1/datasets/evaluation/jobs?status=pending&location=remot')
        self.assertEqual(resp.status_code, 400)

    @mock.patch('db.dataset_eval.get_job')
    @mock.patch('db.dataset.get')
    def test_get_job_details(self, get, get_job):
        self.temporary_login(self.test_user_id)

        get_job.return_value = self.test_job_details
        get.return_value = self.test_dataset
        resp = self.client.get('/api/v1/datasets/evaluation/jobs/7804abe5-58be-4c9c-a787-22b91d031489', content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        expected_job_details = self.test_job_details
        expected_job_details['dataset'] = self.test_dataset
        self.assertEqual(resp.json, expected_job_details)

    @mock.patch('db.dataset_eval.get_job')
    @mock.patch('webserver.views.api.v1.datasets.get_check_dataset')
    def test_get_job_details_no_such_job(self, get_check_dataset, get_job):
        self.temporary_login(self.test_user_id)

        get_job.return_value = None
        resp = self.client.get('/api/v1/datasets/evaluation/jobs/7804abe5-58be-4c9c-a787-22b91d031489', content_type='application/json')
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(json.loads(resp.data), {"message": "No such job"})

    @mock.patch('db.dataset_eval.get_job')
    @mock.patch('webserver.views.api.v1.datasets.get_check_dataset')
    def test_get_job_details_not_public(self, get_check_dataset, get_job):
        self.temporary_login(self.test_user_id)

        get_job.return_value = self.test_job_details
        get_check_dataset.side_effect = webserver.views.api.exceptions.APINotFound('No such job')
        resp = self.client.get('/api/v1/datasets/evaluation/jobs/7804abe5-58be-4c9c-a787-22b91d031489', content_type='application/json')
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(json.loads(resp.data), {"message": "No such job"})

    @mock.patch('db.dataset_eval.get_job')
    def test_get_job_details_invalid_uuid(self, get_job):
        self.temporary_login(self.test_user_id)

        get_job.return_value = self.test_job_details
        resp = self.client.get('/api/v1/datasets/evaluation/jobs/7804abe5-58be-4c9c-a787-22b91d03xxxx', content_type='application/json')
        self.assertEqual(resp.status_code, 404)

        expected_result = {"message": "The requested URL was not found on the server. If you entered the URL manually please check your spelling and try again."}
        self.assertEqual(resp.json, expected_result)

    @mock.patch('db.dataset_eval.get_job')
    def test_get_job_details_internal_server_error(self, get_job):
        self.temporary_login(self.test_user_id)

        get_job.side_effect = InternalServerError()
        resp = self.client.get('/api/v1/datasets/evaluation/jobs/7804abe5-58be-4c9c-a787-22b91d031489', content_type='application/json')
        self.assertEqual(resp.status_code, 500)

        expected_result = {"message": "An unknown error occurred"}
        self.assertEqual(resp.json, expected_result)
