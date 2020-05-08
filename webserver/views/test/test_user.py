from __future__ import absolute_import
from werkzeug.http import http_date
from webserver.testing import AcousticbrainzTestCase
import db.user
import db.api_key


class UserViewsTestCase(AcousticbrainzTestCase):

    def setUp(self):
        super(UserViewsTestCase, self).setUp()

        self.test_user_mb_name = "tester"
        self.test_user_id = db.user.create(self.test_user_mb_name)
        db.user.agree_to_gdpr(self.test_user_mb_name)
        self.test_user = db.user.get(self.test_user_id)

    def generate_api_key(self):
        resp = self.client.get("/user/generate-api-key")
        self.assertStatus(resp, 200)

        resp = self.client.post("/user/generate-api-key")
        self.assertStatus(resp, 200)

        # With logged in user
        self.temporary_login(self.test_user_id)
        resp = self.client.post("/user/generate-api-key")
        self.assertStatus(resp, 200)
        key_1 = db.api_key.get_active(self.test_user_id)
        self.assertIsNotNone(key_1)

        resp = self.client.post("/user/generate-api-key")
        self.assertStatus(resp, 200)
        key_2 = db.api_key.get_active(self.test_user_id)
        self.assertNotEqual(key_1, key_2)

        self.assertTrue(db.api_key.is_active(key_2))
        self.assertFalse(db.api_key.is_active(key_1))

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
