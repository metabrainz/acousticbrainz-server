from webserver.testing import AcousticbrainzTestCase
from flask import url_for


class StatsViewsTestCase(AcousticbrainzTestCase):

    def test_graph(self):
        resp = self.client.get(url_for('stats.graph'))
        self.assert200(resp)

    def test_data(self):
        resp = self.client.get(url_for('stats.data'))
        self.assert200(resp)
