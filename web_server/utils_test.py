from web_server.testing import ServerTestCase
from web_server import utils


class UtilsTestCase(ServerTestCase):
    def test_has_key(self):
        dictionary = {
            'test_1': {
                'inner_test': {
                    'secret_test_1': 'Hey there!',
                    'secret_test_2': 'Bye!',
                },
            },
            'test_2': 'Testing!',
        }

        self.assertTrue(utils._has_key(dictionary, ['test_1', 'inner_test']))
        self.assertTrue(utils._has_key(dictionary, ['test_1', 'inner_test', 'secret_test_2']))
        self.assertTrue(utils._has_key(dictionary, ['test_2']))

        self.assertFalse(utils._has_key(dictionary, ['test_3']))
        self.assertFalse(utils._has_key(dictionary, ['test_1', 'inner_test', 'secret_test_3']))

    def test_sanity_check_data(self):
        data = {
            "metadata": {
                "audio_properties": {
                    "bit_rate": 253569,
                    "codec": "mp3",
                    "length": 280.685699463,
                    "lossless": False,
                },
                "tags": {
                    "file_name": "18 I Was Born for This.mp3",
                    "musicbrainz_recordingid": ["8c12af5a-f9a2-42fa-9dbe-032d7a1f4d5b"],
                },
                "version": {
                    "essentia": "2.1-beta2",
                    "essentia_build_sha": "26c37b627ab5a2028d412893e0969599b764ad4d",
                    "essentia_git_sha": "v2.1_beta2",
                    "extractor": "music 1.0"
                }
            },
            "lowlevel": None,
            "rhythm": None,
            "tonal": None,
        }

        self.assertIsNone(utils.sanity_check_data(data))

        del data['metadata']['tags']['file_name']

        self.assertEquals(utils.sanity_check_data(data), ['metadata', 'tags', 'file_name'])

    def test_clean_metadata(self):
        data = {
            "metadata": {
                "tags": {
                    "file_name": "18 I Was Born for This.mp3",
                    "musicbrainz_recordingid": ["8c12af5a-f9a2-42fa-9dbe-032d7a1f4d5b"],
                    "unknown_tag": "Hello! I am an unknown tag!",
                },
            },
        }
        utils.clean_metadata(data)
        self.assertFalse('unknown_tag' in data['metadata']['tags'])
        self.assertTrue('file_name' in data['metadata']['tags'])

    def test_generate_string(self):
        length = 42
        str_1 = utils.generate_string(length)
        str_2 = utils.generate_string(length)

        self.assertEqual(len(str_1), length)
        self.assertEqual(len(str_2), length)
        self.assertNotEqual(str_1, str_2)  # Generated strings shouldn't be the same
