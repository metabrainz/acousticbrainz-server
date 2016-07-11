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

        time = datetime.datetime
        get_remote_pending_jobs_for_user.return_value = {
            'username': 'tester',
            'jobs': [{
                'job_id': '7804abe5-58be-4c9c-a787-22b91d031489',
                'dataset_name' : 'test',
                'job_created' : str(time)
                }]
            }
        submit = json.dumps({})
        resp = self.client.get('/api/v1/datasets/evaluation/pending-jobs', content_type='application/json')
        self.assertEqual(resp.status_code, 200)

        expected = {
            'success': True,
            'jobs': [{
                'job_id': '7804abe5-58be-4c9c-a787-22b91d031489',
                'dataset_name' : 'test',
                'job_created' : str(time)
                }],
            'username': 'tester'}
        self.assertEqual(resp.json, expected)
