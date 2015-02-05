from acousticbrainz.testing import FlaskTestCase
from flask import url_for


class LoginViewsTestCase(FlaskTestCase):

    def test_login_page(self):
        response = self.client.get(url_for('login.index'))
        self.assert200(response)
