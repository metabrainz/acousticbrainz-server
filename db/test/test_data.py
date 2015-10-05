from db.testing import DatabaseTestCase, TEST_DATA_PATH
import db.exceptions
import db.data
import os.path
import json
import mock
import copy


class DataDBTestCase(DatabaseTestCase):

    def setUp(self):
        super(DataDBTestCase, self).setUp()
        self.test_mbid = "0dad432b-16cc-4bf0-8961-fd31d124b01b"
        self.test_lowlevel_data_json = open(os.path.join(TEST_DATA_PATH, self.test_mbid + '.json')).read()
        self.test_lowlevel_data = json.loads(self.test_lowlevel_data_json)


    @mock.patch("db.data.sanity_check_data")
    @mock.patch("db.data.write_low_level")
    @mock.patch("db.data.clean_metadata")
    def test_submit_low_level_data(self, clean, write, sanity):
        """Submission with valid data"""
        clean.side_effect = lambda x: x
        sanity.return_value = None

        db.data.submit_low_level_data(self.test_mbid, self.test_lowlevel_data)
        write.assert_called_with(self.test_mbid, self.test_lowlevel_data)

    @mock.patch("db.data.sanity_check_data")
    @mock.patch("db.data.write_low_level")
    @mock.patch("db.data.clean_metadata")
    def test_submit_low_level_data_rewrite_keys(self, clean, write, sanity):
        """submit rewrites trackid -> recordingid, and sets lossless to a boolean"""
        clean.side_effect = lambda x: x
        sanity.return_value = None

        input = {"metadata": {"tags": {"musicbrainz_trackid": [self.test_mbid]}, "audio_properties": {"lossless": 1}}}
        output = {"metadata": {"tags": {"musicbrainz_recordingid": [self.test_mbid]}, "audio_properties": {"lossless": True}}}

        db.data.submit_low_level_data(self.test_mbid, input)
        write.assert_called_with(self.test_mbid, output)


    @mock.patch("db.data.sanity_check_data")
    @mock.patch("db.data.write_low_level")
    @mock.patch("db.data.clean_metadata")
    def test_submit_low_level_data_bad_mbid(self, clean, write, sanity):
        """Check that hl write raises an error if the provided mbid is different to what is in the metadata"""
        clean.side_effect = lambda x: x
        sanity.return_value = None

        input = {"metadata": {"tags": {"musicbrainz_recordingid": ["not-the-recording-mbid"]}, "audio_properties": {"lossless": False}}}

        with self.assertRaises(db.exceptions.BadDataException):
            db.data.submit_low_level_data(self.test_mbid, input)


    @mock.patch("db.data.sanity_check_data")
    @mock.patch("db.data.write_low_level")
    @mock.patch("db.data.clean_metadata")
    def test_submit_low_level_data_missing_keys(self, clean, write, sanity):
        """Check that hl write raises an error if some required keys are missing"""
        clean.side_effect = lambda x: x
        sanity.return_value = ["missing", "key"]

        with self.assertRaises(db.exceptions.BadDataException):
            db.data.submit_low_level_data(self.test_mbid, self.test_lowlevel_data)


    def test_write_load_low_level(self):
        """Writing and loading a dict returns the same data"""
        one = {"data": "one", "metadata": {"audio_properties": {"lossless": True}, "version": {"essentia_build_sha": "x"}}}
        db.data.write_low_level(self.test_mbid, one)
        self.assertEqual(one, db.data.load_low_level(self.test_mbid))


    def test_load_low_level_offset(self):
        """If two items with the same mbid are added, you can select between them with offset"""
        one = {"data": "one", "metadata": {"audio_properties": {"lossless": True}, "version": {"essentia_build_sha": "x"}}}
        two = {"data": "two", "metadata": {"audio_properties": {"lossless": True}, "version": {"essentia_build_sha": "x"}}}
        db.data.write_low_level(self.test_mbid, one)
        db.data.write_low_level(self.test_mbid, two)

        self.assertEqual(one, db.data.load_low_level(self.test_mbid))
        self.assertEqual(one, db.data.load_low_level(self.test_mbid, 0))
        self.assertEqual(two, db.data.load_low_level(self.test_mbid, 1))


    def test_load_low_level_none(self):
        """If no data is loaded, or offset is too high, an exception is raised"""
        with self.assertRaises(db.exceptions.NoDataFoundException):
            db.data.load_low_level(self.test_mbid)

        one = {"data": "one", "metadata": {"audio_properties": {"lossless": True}, "version": {"essentia_build_sha": "x"}}}
        db.data.write_low_level(self.test_mbid, one)
        with self.assertRaises(db.exceptions.NoDataFoundException):
            db.data.load_low_level(self.test_mbid, 1)


    def _get_ll_id_from_mbid(self, mbid):
        with db.engine.connect() as connection:
            ret = []
            result = connection.execute("select id from lowlevel where mbid = %s", (mbid, ))
            for row in result:
                ret.append(row[0])
            return ret


    def test_write_load_high_level(self):
        """Writing and loading a dict returns the same data"""
        ll = {"data": "one", "metadata": {"audio_properties": {"lossless": True}, "version": {"essentia_build_sha": "x"}}}
        hl = {"highlevel": "data"}

        build_sha = "test"
        db.data.write_low_level(self.test_mbid, ll)
        ll_id = self._get_ll_id_from_mbid(self.test_mbid)[0]
        db.data.write_high_level(self.test_mbid, ll_id, hl, build_sha)

        self.assertEqual(hl, db.data.load_high_level(self.test_mbid))


    def test_load_high_level_offset(self):
        # If there are two lowlevel items, but only one highlevel, we should raise NoDataFound
        second_data = copy.deepcopy(self.test_lowlevel_data)
        second_data["metadata"]["tags"]["album"] = ["Another album"]

        db.data.write_low_level(self.test_mbid, self.test_lowlevel_data)
        db.data.write_low_level(self.test_mbid, second_data)
        ll_id1, ll_id2 = self._get_ll_id_from_mbid(self.test_mbid)

        build_sha = "sha"
        hl1 = {"highlevel": "one"}
        hl2 = {"highlevel": "two"}
        db.data.write_high_level(self.test_mbid, ll_id1, hl1, build_sha)
        # First highlevel item
        self.assertEqual(hl1, db.data.load_high_level(self.test_mbid))
        self.assertEqual(hl1, db.data.load_high_level(self.test_mbid, offset=0))

        # second has a ll, but no hl => exception
        with self.assertRaises(db.exceptions.NoDataFoundException):
            db.data.load_high_level(self.test_mbid, offset=1)

        # after adding the hl, no error
        db.data.write_high_level(self.test_mbid, ll_id2, hl2, build_sha)
        self.assertEqual(hl2, db.data.load_high_level(self.test_mbid, offset=1))


    def test_load_high_level_offset_reverse(self):
        # If hl are added in a different order to ll, offset should return ll order
        second_data = copy.deepcopy(self.test_lowlevel_data)
        second_data["metadata"]["tags"]["album"] = ["Another album"]

        db.data.write_low_level(self.test_mbid, self.test_lowlevel_data)
        db.data.write_low_level(self.test_mbid, second_data)
        ll_id1, ll_id2 = self._get_ll_id_from_mbid(self.test_mbid)

        build_sha = "sha"
        hl1 = {"highlevel": "one"}
        hl2 = {"highlevel": "two"}
        db.data.write_high_level(self.test_mbid, ll_id2, hl2, build_sha)
        db.data.write_high_level(self.test_mbid, ll_id1, hl1, build_sha)

        self.assertEqual(hl1, db.data.load_high_level(self.test_mbid))
        self.assertEqual(hl2, db.data.load_high_level(self.test_mbid, offset=1))


    def test_load_high_level_none(self):
        """If no data is loaded, or offset is too high, an exception is raised"""

        # no data
        with self.assertRaises(db.exceptions.NoDataFoundException):
            db.data.load_high_level(self.test_mbid, offset=0)

        db.data.write_low_level(self.test_mbid, self.test_lowlevel_data)
        ll_id1 = self._get_ll_id_from_mbid(self.test_mbid)[0]

        build_sha = "sha"
        hl1 = {"highlevel": "one"}
        db.data.write_high_level(self.test_mbid, ll_id1, hl1, build_sha)

        with self.assertRaises(db.exceptions.NoDataFoundException):
            db.data.load_high_level(self.test_mbid, offset=1)


    def test_count_lowlevel(self):
        db.data.submit_low_level_data(self.test_mbid, self.test_lowlevel_data)
        self.assertEqual(1, db.data.count_lowlevel(self.test_mbid))
        # Exact same data is deduplicated
        db.data.submit_low_level_data(self.test_mbid, self.test_lowlevel_data)
        self.assertEqual(1, db.data.count_lowlevel(self.test_mbid))

        # make a copy of the data and change it
        second_data = copy.deepcopy(self.test_lowlevel_data)
        second_data["metadata"]["tags"]["album"] = ["Another album"]
        db.data.submit_low_level_data(self.test_mbid, second_data)
        self.assertEqual(2, db.data.count_lowlevel(self.test_mbid))


    def test_get_summary_data(self):
        pass

class DataUtilTestCase(DatabaseTestCase):
    """ Tests for utility methods in db/data. Should be moved out of db at some time. """

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

        self.assertTrue(db.data._has_key(dictionary, ['test_1', 'inner_test']))
        self.assertTrue(db.data._has_key(dictionary, ['test_1', 'inner_test', 'secret_test_2']))
        self.assertTrue(db.data._has_key(dictionary, ['test_2']))

        self.assertFalse(db.data._has_key(dictionary, ['test_3']))
        self.assertFalse(db.data._has_key(dictionary, ['test_1', 'inner_test', 'secret_test_3']))

    def test_sanity_check_data(self):
        d = {
            "metadata": {
                "audio_properties": {
                    "bit_rate": 253569,
                    "codec": "mp3",
                    "length": 280.685699463,
                    "lossless": False,
                },
                "tags": {
                    "file_name": "example.mp3",
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
        self.assertIsNone(db.data.sanity_check_data(d))
        del d['metadata']['tags']['file_name']
        self.assertEquals(db.data.sanity_check_data(d), ['metadata', 'tags', 'file_name'])

    def test_clean_metadata(self):
        d = {
            "metadata": {
                "tags": {
                    "file_name": "example.mp3",
                    "musicbrainz_recordingid": ["8c12af5a-f9a2-42fa-9dbe-032d7a1f4d5b"],
                    "unknown_tag": "Hello! I am an unknown tag!",
                },
            },
        }
        db.data.clean_metadata(d)
        self.assertFalse('unknown_tag' in d['metadata']['tags'])
        self.assertTrue('file_name' in d['metadata']['tags'])
