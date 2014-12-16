from acousticbrainz.testing import FlaskTestCase
from flask import url_for


class StatsViewsTestCase(FlaskTestCase):

    def test_statistics_graph(self):
        resp = self.client.get(url_for('stats.statistics_graph'))
        self.assert200(resp)

    def test_statistics_data(self):
        resp = self.client.get(url_for('stats.statistics_data'))
        self.assert200(resp)
