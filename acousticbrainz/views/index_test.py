from acousticbrainz.testing import FlaskTestCase
from flask import url_for


class IndexViewsTestCase(FlaskTestCase):

    def test_index(self):
        resp = self.client.get(url_for('index.index'))
        self.assert200(resp)
