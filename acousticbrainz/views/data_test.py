from acousticbrainz.testing import FlaskTestCase
from flask import url_for


class DataViewsTestCase(FlaskTestCase):

    def test_api(self):
        resp = self.client.get(url_for('data.api'))
        self.assertEquals(resp.status_code, 302)  # Should redirect to data page

    def test_data(self):
        resp = self.client.get(url_for('data.data'))
        self.assert200(resp)
