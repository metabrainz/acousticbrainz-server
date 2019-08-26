from __future__ import absolute_import
import json

import mock
from flask import url_for

from db import user
import db.similarity
from webserver.testing import ServerTestCase, TEST_DATA_PATH

class SimilarityViewsTestCase(ServerTestCase):
    
    def setUp(self):
        super(SimilarityViewsTestCase, self).setUp()

        self.test_user_mb_name = "tester"
        self.test_user_id = user.create(self.test_user_mb_name)
        user.agree_to_gdpr(self.test_user_mb_name)

    @mock.patch('webserver.external.musicbrainz.get_recording_by_id')
    def test_metrics(self, get_recording_by_id):
        # If recording is not submitted, NotFound is raised
        get_recording_by_id.side_effect = FakeMusicBrainz.get_recording_by_id
        mbid = '0dad432b-16cc-4bf0-8961-fd31d124b01b'
        resp = self.client.get(url_for('similarity.metrics', mbid=mbid))
        self.assertEqual(404, resp.status_code)

        # With submitted recording
        self.load_low_level_data(mbid)
        resp = self.client.get(url_for('similarity.metrics', mbid=mbid))
        self.assertEqual(200, resp.status_code)

    @mock.patch('webserver.external.musicbrainz.get_recording_by_id')
    def test_get_similar(self, get_recording_by_id):
        # Not logged in, redirect
        get_recording_by_id.side_effect = FakeMusicBrainz.get_recording_by_id
        mbid = '0dad432b-16cc-4bf0-8961-fd31d124b01b'
        metric = 'mfccs'
        resp = self.client.get(url_for('similarity.get_similar', mbid=mbid, metric=metric))
        self.assertEqual(302, resp.status_code)

        # Logged in without submitted recording, 404
        self.temporary_login(self.test_user_id)
        resp = self.client.get(url_for('similarity.get_similar', mbid=mbid, metric=metric))
        self.assertEqual(404, resp.status_code)

        # Logged in with submitted recording, 200
        self.load_low_level_data(mbid)
        resp = self.client.get(url_for('similarity.get_similar', mbid=mbid, metric=metric))
        self.assertEqual(200, resp.status_code)

        # Metric does not exist, NotFound is raised
        metric = 'x'
        resp = self.client.get(url_for('similarity.get_similar', mbid=mbid, metric=metric))
        self.assertEqual(404, resp.status_code)

    def test_get_similar_service(self):
        # Without login, 401
        mbid = '0dad432b-16cc-4bf0-8961-fd31d124b01b'
        metric = 'mfccs'
        resp = self.client.get(url_for('similarity.get_similar_service', mbid=mbid, metric=metric))
        self.assertEqual(401, resp.status_code)

        # Logged in, no submitted recording causes redirect
        self.temporary_login(self.test_user_id)
        resp = self.client.get(url_for('similarity.get_similar_service', mbid=mbid, metric=metric))
        self.assertEqual(302, resp.status_code)
        
        # Submitted recording, no Annoy index causes redirects
        self.load_low_level_data(mbid)
        resp = self.client.get(url_for('similarity.get_similar_service', mbid=mbid, metric=metric))
        self.assertEqual(302, resp.status_code)

    @mock.patch("db.similarity.submit_eval_results")
    @mock.patch("webserver.views.similarity._get_extended_info")
    @mock.patch("webserver.views.similarity.AnnoyModel")
    def test_get_similar_service_index(self, annoy_model, _get_extended_info, submit_eval_results):
        mbid = '0dad432b-16cc-4bf0-8961-fd31d124b01b'
        metric = 'mfccs'
        recordings = [('0dad432b-16cc-4bf0-8961-fd31d124b01b', 0), ('0dad432b-16cc-4bf0-8961-fd31d124b01b', 1)]
        distances = [0.5, 1.2]
        ids = [0, 1]
        expected_result = [ids, recordings, distances]
        annoy_mock = mock.Mock()
        annoy_mock.get_nns_by_mbid.return_value = expected_result
        annoy_model.return_value = annoy_mock

        _get_extended_info.side_effect = [{"mock_info": "info1"}, {"mock_info": "info2"}]
        submit_eval_results.return_value = 1
        category, metric, description = db.similarity.get_metric_info(metric)

        self.load_low_level_data(mbid)
        self.temporary_login(self.test_user_id)

        expected = {"metadata": [{"mock_info": "info1"}, {"mock_info": "info2"}],
                    "metric": {"category": category, "description": description},
                    "submitted": False}

        resp = self.client.get(url_for('similarity.get_similar_service', mbid=mbid, metric=metric))
        self.assertEqual(200, resp.status_code)
    
    @mock.patch("db.similarity.add_evaluation")
    def test_add_evaluations(self, add_evaluation):
        mbid = '0dad432b-16cc-4bf0-8961-fd31d124b01b'
        metric = 'mfccs'

        form_data = {"feedback": "accurate", "suggestion": "test"}
        form_data_two = {"feedback": None, "suggestion": "test"}
        test_data = {"form": {"0": form_data, 
                              "1": form_data_two},
                    "metadata": [{"eval_id": 1, "lowlevel_id": 0},
                                 {"eval_id": 1, "lowlevel_id": 1}]
        }

        # No login, 401
        resp = self.client.post(url_for('similarity.add_evaluations', mbid=mbid, metric=metric),
                                headers={"Content-Type": "application/json"},
                                data=json.dumps(test_data))
        self.assertEqual(401, resp.status_code)
        add_evaluation.assert_not_called()

        self.temporary_login(self.test_user_id)
        user_id = 1
        eval_id = 1
        eval_calls = [mock.call(user_id, eval_id, 0, form_data["feedback"], form_data["suggestion"]),
                      mock.call(user_id, eval_id, 1, form_data_two["feedback"], form_data_two["suggestion"])]

        resp = self.client.post(url_for('similarity.add_evaluations', mbid=mbid, metric=metric),
                                headers={"Content-Type": "application/json"},
                                data=json.dumps(test_data))
        self.assertEqual(200, resp.status_code)
        expected_json = {"success": True}
        self.assertEqual(expected_json, resp.json)
        add_evaluation.assert_has_calls(eval_calls)
    
    @mock.patch("db.similarity.add_evaluation")
    def test_add_evaluations_missing_data(self, add_evaluation):
        # Form data missing, 400 error returned
        self.temporary_login(self.test_user_id)
        mbid = '0dad432b-16cc-4bf0-8961-fd31d124b01b'
        metric = 'mfccs'

        test_data = {"form": None,
                    "metadata": [{"eval_id": 1, "lowlevel_id": 0},
                                 {"eval_id": 1, "lowlevel_id": 1}]
        }
        resp = self.client.post(url_for('similarity.add_evaluations', mbid=mbid, metric=metric),
                                headers={"Content-Type": "application/json"},
                                data=json.dumps(test_data))
        self.assertEqual(400, resp.status_code)
        expected_json = {
            'success': False,
            'error': "Request does not contain form data."
        }
        self.assertEqual(expected_json, resp.json)
        add_evaluation.assert_not_called()

        # Metadata missing, 400 error returned
        form_data = {"feedback": "accurate", "suggestion": "test"}
        form_data_two = {"feedback": None, "suggestion": "test"}
        test_data = {"form": {"0": form_data, 
                              "1": form_data_two},
                    "metadata": None
        }
        resp = self.client.post(url_for('similarity.add_evaluations', mbid=mbid, metric=metric),
                                headers={"Content-Type": "application/json"},
                                data=json.dumps(test_data))
        self.assertEqual(400, resp.status_code)
        expected_json = {
            'success': False,
            'error': "Request does not contain metadata for similar recordings."
        }
        self.assertEqual(expected_json, resp.json)
        add_evaluation.assert_not_called()


class FakeMusicBrainz(object):
    
    @staticmethod
    def get_recording_by_id(mbid):
        return {
            'artist-credit':[
                {
                    'artist':{
                        'sort-name':'Wintory, Austin',
                        'disambiguation':'American video game music composer',
                        'id':'78f15956-c5e1-46d6-a46b-fa6f46681ec8',
                        'name':'Austin Wintory'
                    }
                }
            ],
            'title':'Nascence',
            'id':'0dad432b-16cc-4bf0-8961-fd31d124b01b',
            'length':'107000',
            'release-list':[
                {
                    'status':'Official',
                    'release-event-count':1,
                    'barcode':'',
                    'title':'Journey',
                    'country':'XW',
                    'medium-count':1,
                    'release-event-list':[
                        {
                            'date':'2012-04-10',
                            'area':{
                                'sort-name':'[Worldwide]',
                                'iso-3166-1-code-list':[
                                    'XW'
                                ],
                                'id':'525d4e18-3d00-31b9-a58b-a146a916de8f',
                                'name':'[Worldwide]'
                            }
                        }
                    ],
                    'packaging':'None',
                    'medium-list':[
                        {
                            'position':'1',
                            'format':'Digital Media',
                            'track-list':[
                                {
                                    'title':'Nascence',
                                    'number':'1',
                                    'length':'107000',
                                    'position':'1',
                                    'id':'09999a96-3d26-33ff-b0dc-56464be6716e',
                                    'track_or_recording_length':'107000'
                                }
                            ],
                            'track-count':18
                        }
                    ],
                    'text-representation':{
                        'language':'eng',
                        'script':'Latn'
                    },
                    'date':'2012-04-10',
                    'quality':'normal',
                    'id':'1f3abcda-15a7-4465-92c6-9926cdc4f247'
                }
            ],
            'release-count':3,
            'artist-credit-phrase':'Austin Wintory'
        }