# -*- coding: utf-8 -*-
from db.testing import DatabaseTestCase
import db.user


class UserTestCase(DatabaseTestCase):

    def test_create(self):
        user_id = db.user.create("fuzzy_dunlop")

        self.assertIsNotNone(db.user.get(user_id))

        # Testing Unicode
        user_id = db.user.create(u"Пользователь")
        self.assertIsNotNone(user_id)

    def test_get(self):
        user_id = db.user.create("fuzzy_dunlop")
        self.assertIsNotNone(db.user.get(user_id))

        self.assertIsNone(db.user.get(user_id + 2))

    def test_get_by_mb_id(self):
        self.assertIsNone(db.user.get_by_mb_id("fuzzy"))

        musicbrainz_id = "fuzzy_dunlop"
        user_id = db.user.create(musicbrainz_id)
        user = db.user.get_by_mb_id(musicbrainz_id)
        self.assertIsNotNone(user)
        self.assertEqual(user["id"], user_id)

    def test_get_or_create(self):
        musicbrainz_id = "User"
        user = db.user.get_or_create(musicbrainz_id)
        self.assertIsNotNone(user)

        same_user = db.user.get_or_create(musicbrainz_id)
        self.assertEqual(user["id"], same_user["id"])

        # Testing Unicode
        musicbrainz_id = u"Пользователь"
        user = db.user.get_or_create(musicbrainz_id)
        self.assertIsNotNone(user)

        same_user = db.user.get_or_create(musicbrainz_id)
        self.assertEqual(user["id"], same_user["id"])
