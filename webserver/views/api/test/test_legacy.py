from __future__ import absolute_import

from unittest import mock
import six

import db.exceptions
from webserver.testing import AcousticbrainzTestCase
from webserver.testing import DB_TEST_DATA_PATH
from flask import url_for
import os


class LegacyViewsTestCase(AcousticbrainzTestCase):

    def test_submit_low_level(self):
        mbid = '0dad432b-16cc-4bf0-8961-fd31d124b01b'

        with open(os.path.join(DB_TEST_DATA_PATH, mbid + '.json')) as json_file:
            with self.app.test_client() as client:
                sub_resp = client.post("/%s/low-level" % mbid,
                                       data=json_file.read(),
                                       content_type='application/json')
                self.assertEqual(sub_resp.status_code, 200)

        # Getting from the new API
        resp = self.client.get("/api/v1/%s/low-level" % mbid)
        self.assertEqual(resp.status_code, 200)

    def test_get_low_level(self):
        mbid = '0dad432b-16cc-4bf0-8961-fd31d124b01b'
        resp = self.client.get(url_for('api.get_low_level', mbid=mbid))
        self.assertEqual(resp.status_code, 404)

        self.load_low_level_data(mbid)

        resp = self.client.get(url_for('api.get_low_level', mbid=mbid))
        self.assertEqual(resp.status_code, 200)

        # works regardless of the case or format of the uuid
        mbid = '0DAD432B-16CC-4BF0-8961-FD31D124B01B'
        resp = self.client.get(url_for('api.get_low_level', mbid=mbid))
        self.assertEqual(resp.status_code, 200)
        mbid = '0DAD432B16CC4BF08961FD31D124B01B'
        resp = self.client.get(url_for('api.get_low_level', mbid=mbid))
        self.assertEqual(resp.status_code, 200)

    @mock.patch('db.data.load_high_level')
    def test_get_high_level(self, load_high_level):
        mbid = '0dad432b-16cc-4bf0-8961-fd31d124b01b'
        load_high_level.side_effect = db.exceptions.NoDataFoundException
        resp = self.client.get(url_for('api.get_high_level', mbid=mbid))
        self.assertEqual(resp.status_code, 404)

        load_high_level.side_effect = None
        load_high_level.return_value = '{}'

        resp = self.client.get(url_for('api.get_high_level', mbid=mbid))
        self.assertEqual(resp.status_code, 200)
        load_high_level.assert_called_with(mbid, 0)

        # works regardless of the case or format of the uuid
        mbid = '0DAD432B-16CC-4BF0-8961-FD31D124B01B'
        resp = self.client.get(url_for('api.get_high_level', mbid=mbid))
        self.assertEqual(resp.status_code, 200)
        mbid = '0DAD432B16CC4BF08961FD31D124B01B'
        resp = self.client.get(url_for('api.get_high_level', mbid=mbid))
        self.assertEqual(resp.status_code, 200)

    def test_count(self):
        mbid = '0dad432b-16cc-4bf0-8961-fd31d124b01b'
        resp = self.client.get(url_for('api.count', mbid=mbid))
        expected = {'mbid': mbid, 'count': 0}
        self.assertEqual(resp.status_code, 200)
        six.assertCountEqual(self, resp.json, expected)

        self.load_low_level_data(mbid)
        expected = {'mbid': mbid, 'count': 1}
        resp = self.client.get(url_for('api.count', mbid=mbid))
        self.assertEqual(resp.status_code, 200)
        six.assertCountEqual(self, resp.json, expected)

        # upper-case and format
        mbid = '0DAD432B-16CC-4BF0-8961-FD31D124B01B'
        resp = self.client.get(url_for('api.count', mbid=mbid.upper()))
        self.assertEqual(resp.status_code, 200)
        # mbid stays lower-case in the response
        six.assertCountEqual(self, resp.json, expected)
        mbid = '0DAD432B16CC4BF08961FD31D124B01B'
        resp = self.client.get(url_for('api.count', mbid=mbid.upper()))
        self.assertEqual(resp.status_code, 200)

    def test_cors_headers(self):
        mbid = '0dad432b-16cc-4bf0-8961-fd31d124b01b'
        self.load_low_level_data(mbid)

        resp = self.client.get(url_for('api.get_low_level', mbid=mbid))
        self.assertEqual(resp.headers['Access-Control-Allow-Origin'], '*')
