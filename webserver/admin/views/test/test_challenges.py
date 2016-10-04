from webserver.testing import ServerTestCase
from flask import url_for


class ChallengesTestCase(ServerTestCase):

    def test_access(self):
        self.assertStatus(self.client.get(url_for('challengesview.index')), 302)
