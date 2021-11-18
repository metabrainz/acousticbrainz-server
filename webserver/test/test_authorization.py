import json
from flask import url_for
from werkzeug.datastructures import Headers

from db import api_key, user
from webserver.testing import AcousticbrainzTestCase


class AuthorizationTestCase(AcousticbrainzTestCase):

    def setUp(self):
        super(AuthorizationTestCase, self).setUp()

        self.test_user_mb_name = "tester"
        self.test_user_id = user.create(self.test_user_mb_name)
        self.api_key = api_key.generate(self.test_user_id)
        user.agree_to_gdpr(self.test_user_mb_name)

    def test_website_login_required(self):
        """Visiting some page that requires the user to be logged in should
        redirect to the login page if the user isn't logged in"""

        resp = self.client.get(url_for("datasets.create"))
        self.assertStatus(resp, 302)
        self.assertTrue(resp.location.endswith("/login/?next=%2Fdatasets%2Fcreate"))

        # With logged in user
        self.temporary_login(self.test_user_id)

        resp = self.client.get(url_for("datasets.create"))
        self.assert200(resp)

    def test_api_token_or_session_required(self):
        """An API method that allows either a login session or an Authorization header"""

        # Not logged in
        submit = json.dumps({"a": "thing"})
        resp = self.client.post("/api/v1/datasets/", data=submit, content_type="application/json")
        self.assert401(resp)

        # Invalid auth token
        headers = Headers({"Authorization": "Token foo"})
        resp = self.client.post("/api/v1/datasets/", data=submit, content_type="application/json", headers=headers)
        self.assert401(resp)

        # Auth token
        headers = Headers({"Authorization": "Token " + self.api_key})
        resp = self.client.post("/api/v1/datasets/", data=submit, content_type="application/json", headers=headers)
        # we expect 400 because the data is invalid, but we got passed the auth requirement
        self.assert400(resp)

        # Session, no token
        self.temporary_login(self.test_user_id)
        resp = self.client.post("/api/v1/datasets/", data=submit, content_type="application/json")
        # we expect 400 because the data is invalid, but we passed the auth requirement
        self.assert400(resp)

    def test_service_session_required(self):
        # Not logged in, unauthorized
        resp = self.client.post(url_for("datasets.create_service"), data="not-json-but-thats-ok")
        self.assert401(resp)

        # Valid token, unauthorized
        headers = Headers({"Authorization": "Token " + self.api_key})
        resp = self.client.post(url_for("datasets.create_service"), data="not-json-but-thats-ok", headers=headers)
        self.assert401(resp)

        # Logged in, OK
        self.temporary_login(self.test_user_id)
        resp = self.client.post(url_for("datasets.create_service"), data="not-json-but-thats-ok")
        self.assert400(resp)
