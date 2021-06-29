from webserver.testing import AcousticbrainzTestCase
from flask import url_for


class ChallengesTestCase(AcousticbrainzTestCase):

    def test_access(self):
        self.assertStatus(self.client.get(url_for('challengesview.index')), 302)
