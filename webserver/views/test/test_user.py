from __future__ import absolute_import
from werkzeug.http import http_date
from webserver.testing import ServerTestCase
import db.user


class UserViewsTestCase(ServerTestCase):

    def setUp(self):
        super(UserViewsTestCase, self).setUp()

        self.test_user_mb_name = "tester"
        self.test_user_id = db.user.create(self.test_user_mb_name)
        self.test_user = db.user.get(self.test_user_id)

    def test_info(self):
        resp = self.client.get("/user-info")
        self.assertEqual(resp.json, {
            "user": None,
        })

        # With logged in user
        self.temporary_login(self.test_user_id)
        resp = self.client.get("/user-info")
        self.assertEqual(resp.json, {
            "user": {
                "id": self.test_user["id"],
                "created": http_date(self.test_user["created"]),
                "musicbrainz_id": self.test_user["musicbrainz_id"],
            },
        })
