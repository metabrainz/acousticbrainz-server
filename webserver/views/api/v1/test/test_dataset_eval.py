from __future__ import absolute_import
from webserver.testing import ServerTestCase
from db.testing import TEST_DATA_PATH
import db.exceptions
import db.dataset
import db.dataset_eval
import db.api_key
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
