# -*- coding: utf-8 -*-
from web_server.testing import ServerTestCase
from web_server.data import user as user_data


class UserTestCase(ServerTestCase):

    def test_create(self):
        user_id = user_data.create("fuzzy_dunlop")

        self.assertIsNotNone(user_data.get(user_id))

        # Testing Unicode
        user_id = user_data.create(u"Пользователь")
        self.assertIsNotNone(user_id)

    def test_get(self):
        user_id = user_data.create("fuzzy_dunlop")
        self.assertIsNotNone(user_data.get(user_id))

        self.assertIsNone(user_data.get(user_id + 2))

    def test_get_by_mb_id(self):
        self.assertIsNone(user_data.get_by_mb_id("fuzzy"))

        musicbrainz_id = "fuzzy_dunlop"
        user_id = user_data.create(musicbrainz_id)
        user = user_data.get_by_mb_id(musicbrainz_id)
        self.assertIsNotNone(user)
        self.assertEqual(user.id, user_id)

    def test_get_or_create(self):
        musicbrainz_id = "User"
        user = user_data.get_or_create(musicbrainz_id)
        self.assertIsNotNone(user)

        same_user = user_data.get_or_create(musicbrainz_id)
        self.assertEqual(user.id, same_user.id)

        # Testing Unicode
        musicbrainz_id = u"Пользователь"
        user = user_data.get_or_create(musicbrainz_id)
        self.assertIsNotNone(user)

        same_user = user_data.get_or_create(musicbrainz_id)
        self.assertEqual(user.id, same_user.id)
