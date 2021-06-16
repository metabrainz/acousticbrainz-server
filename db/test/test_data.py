import copy
import json
import os.path

import mock
import copy
import uuid
import sqlalchemy

import db.data
import db.exceptions
from webserver.testing import AcousticbrainzTestCase, DB_TEST_DATA_PATH, gid_types


class DataDBTestCase(AcousticbrainzTestCase):

    def setUp(self):
        super(DataDBTestCase, self).setUp()
        self.test_mbid = "0dad432b-16cc-4bf0-8961-fd31d124b01b"
        self.test_lowlevel_data_json = open(os.path.join(DB_TEST_DATA_PATH, self.test_mbid + '.json')).read()
        self.test_lowlevel_data = json.loads(self.test_lowlevel_data_json)

        self.test_mbid_two = 'e8afe383-1478-497e-90b1-7885c7f37f6e'
        self.test_lowlevel_data_json_two = open(os.path.join(DB_TEST_DATA_PATH, self.test_mbid_two + '.json')).read()
        self.test_lowlevel_data_two = json.loads(self.test_lowlevel_data_json_two)

    @mock.patch("db.data.sanity_check_data")
    @mock.patch("db.data.write_low_level")
    @mock.patch("db.data.clean_metadata")
    def test_submit_low_level_data(self, clean, write, sanity):
        """Submission with valid data"""
        clean.side_effect = lambda x: x
        sanity.return_value = None

        db.data.submit_low_level_data(self.test_mbid, self.test_lowlevel_data, gid_types.GID_TYPE_MBID)
        write.assert_called_with(self.test_mbid, self.test_lowlevel_data, gid_types.GID_TYPE_MBID)

    @mock.patch("db.data.sanity_check_data")
    @mock.patch("db.data.write_low_level")
    @mock.patch("db.data.clean_metadata")
    def test_submit_low_level_data_rewrite_keys(self, clean, write, sanity):
        """submit rewrites trackid -> recordingid, and sets lossless to a boolean"""
        clean.side_effect = lambda x: x
        sanity.return_value = None

        input = {"metadata": {"tags": {"musicbrainz_trackid": [self.test_mbid]}, "audio_properties": {"lossless": 1}}}
        output = {
            "metadata": {"tags": {"musicbrainz_recordingid": [self.test_mbid]}, "audio_properties": {"lossless": True}}}

        db.data.submit_low_level_data(self.test_mbid, input, gid_types.GID_TYPE_MBID)
        write.assert_called_with(self.test_mbid, output, gid_types.GID_TYPE_MBID)

        input = {"metadata": {"tags": {"musicbrainz_trackid": [self.test_mbid]}, "audio_properties": {"lossless": 1}}}
        db.data.submit_low_level_data(self.test_mbid, input, gid_types.GID_TYPE_MSID)
        write.assert_called_with(self.test_mbid, output, gid_types.GID_TYPE_MSID)

    @mock.patch("db.data.sanity_check_data")
    @mock.patch("db.data.write_low_level")
    @mock.patch("db.data.clean_metadata")
    def test_submit_low_level_data_bad_mbid(self, clean, write, sanity):
        """Check that hl write raises an error if the provided mbid is different to what is in the metadata"""
        clean.side_effect = lambda x: x
        sanity.return_value = None

        input = {"metadata": {"tags": {"musicbrainz_recordingid": ["not-the-recording-mbid"]},
                              "audio_properties": {"lossless": False}}}

        with self.assertRaises(db.exceptions.BadDataException):
            db.data.submit_low_level_data(self.test_mbid, input, gid_types.GID_TYPE_MBID)

    @mock.patch("db.data.sanity_check_data")
    @mock.patch("db.data.write_low_level")
    @mock.patch("db.data.clean_metadata")
    def test_submit_low_level_data_missing_keys(self, clean, write, sanity):
        """Check that hl write raises an error if some required keys are missing"""
        clean.side_effect = lambda x: x
        sanity.return_value = ["missing", "key"]

        with self.assertRaises(db.exceptions.BadDataException):
            db.data.submit_low_level_data(self.test_mbid, self.test_lowlevel_data, gid_types.GID_TYPE_MBID)

    def test_get_next_submission_offset(self):
        # Check that next max offset is returned
        with db.engine.connect() as connection:
            one = {"data": "one",
                   "metadata": {"audio_properties": {"lossless": True}, "version": {"essentia_build_sha": "x"}}}
            two = {"data": "two",
                   "metadata": {"audio_properties": {"lossless": True}, "version": {"essentia_build_sha": "x"}}}
            three = {"data": "three",
                     "metadata": {"audio_properties": {"lossless": True}, "version": {"essentia_build_sha": "x"}}}

            db.data.write_low_level(self.test_mbid, one, gid_types.GID_TYPE_MBID)
            self.assertEqual(1, db.data.get_next_submission_offset(connection, self.test_mbid))

            # Adding second submission, max offset is incremented
            db.data.write_low_level(self.test_mbid, two, gid_types.GID_TYPE_MBID)
            self.assertEqual(2, db.data.get_next_submission_offset(connection, self.test_mbid))

            # Before any submissions exist, returns 0
            self.assertEqual(0, db.data.get_next_submission_offset(connection, self.test_mbid_two))

            db.data.write_low_level(self.test_mbid_two, three, gid_types.GID_TYPE_MBID)
            self.assertEqual(1, db.data.get_next_submission_offset(connection, self.test_mbid_two))

    def test_write_load_low_level(self):
        """Writing and loading a dict returns the same data"""
        one = {"data": "one",
               "metadata": {"audio_properties": {"lossless": True}, "version": {"essentia_build_sha": "x"}}}
        db.data.write_low_level(self.test_mbid, one, gid_types.GID_TYPE_MBID)
        self.assertEqual(one, db.data.load_low_level(self.test_mbid))

    def test_write_lowlevel_invalid_data(self):
        """Trying to submit data with invalid utf8 sequences raises an error"""
        one = {"data": u"\uc544\uc774\uc720 (IU)\udc93",
               "metadata": {"audio_properties": {"lossless": True}, "version": {"essentia_build_sha": "x"}}}

        with self.assertRaises(db.exceptions.BadDataException):
            db.data.write_low_level(self.test_mbid, one, gid_types.GID_TYPE_MBID)

    def test_load_low_level_offset(self):
        """If two items with the same mbid are added, you can select between them with offset"""
        one = {"data": "one",
               "metadata": {"audio_properties": {"lossless": True}, "version": {"essentia_build_sha": "x"}}}
        two = {"data": "two",
               "metadata": {"audio_properties": {"lossless": True}, "version": {"essentia_build_sha": "x"}}}
        db.data.write_low_level(self.test_mbid, one, gid_types.GID_TYPE_MBID)
        db.data.write_low_level(self.test_mbid, two, gid_types.GID_TYPE_MBID)

        self.assertEqual(one, db.data.load_low_level(self.test_mbid))
        self.assertEqual(one, db.data.load_low_level(self.test_mbid, 0))
        self.assertEqual(two, db.data.load_low_level(self.test_mbid, 1))

    def test_load_low_level_uuid_case(self):
        """A query with an upper-case uuid will return the correct data"""
        one = {"data": "one",
               "metadata": {"audio_properties": {"lossless": True}, "version": {"essentia_build_sha": "x"}}}
        db.data.write_low_level(self.test_mbid, one, gid_types.GID_TYPE_MBID)

        self.assertEqual(one, db.data.load_low_level(self.test_mbid.upper()))

        many_ll_expected = {
            self.test_mbid: {'0': one}
        }
        recordings = [(self.test_mbid.upper(), 0)]

        self.assertEqual(many_ll_expected, db.data.load_many_low_level(list(recordings)))

    def test_load_low_level_none(self):
        """If no lowlevel data is loaded, or offset is too high, an exception is raised"""
        with self.assertRaises(db.exceptions.NoDataFoundException):
            db.data.load_low_level(self.test_mbid)

        one = {"data": "one",
               "metadata": {"audio_properties": {"lossless": True}, "version": {"essentia_build_sha": "x"}}}
        db.data.write_low_level(self.test_mbid, one, gid_types.GID_TYPE_MBID)
        with self.assertRaises(db.exceptions.NoDataFoundException):
            db.data.load_low_level(self.test_mbid, 1)

    def _get_ll_id_from_mbid(self, mbid):
        with db.engine.connect() as connection:
            ret = []
            result = connection.execute("select id from lowlevel where gid = %s", (mbid,))
            for row in result:
                ret.append(row[0])
            return ret

    def test_load_many_low_level(self):
        """Lowlevel data corresponds to the specified offsets, returns first submission without offset"""
        one = {"data": "one",
               "metadata": {"audio_properties": {"lossless": True}, "version": {"essentia_build_sha": "x"}}}
        two = {"data": "two",
               "metadata": {"audio_properties": {"lossless": True}, "version": {"essentia_build_sha": "x"}}}
        three = {"data": "three",
                 "metadata": {"audio_properties": {"lossless": True}, "version": {"essentia_build_sha": "x"}}}
        db.data.write_low_level(self.test_mbid, one, gid_types.GID_TYPE_MBID)
        db.data.write_low_level(self.test_mbid, two, gid_types.GID_TYPE_MBID)
        db.data.write_low_level(self.test_mbid_two, three, gid_types.GID_TYPE_MBID)

        recordings = [(self.test_mbid, 0),
                      (self.test_mbid, 1),
                      (self.test_mbid_two, 0)]

        ll_expected = {
            self.test_mbid: {'0': one, '1': two},
            self.test_mbid_two: {'0': three}
        }

        self.assertEqual(ll_expected, db.data.load_many_low_level(list(recordings)))

    def test_load_many_low_level_none(self):
        """If offset is too high or there are no submissions for the mbid, it is skipped."""

        # No submitted lowlevel data for any mbid, and offset combinations
        recordings = [('4ee71816-e0be-4257-a5f9-98dca3ec8bcd', 0),
                      ('48877286-42d4-4b0a-a1e0-d703a587f64b', 1),
                      ('ffcc4249-28bb-4c91-9195-a60b21d4fb94', 0)]
        self.assertEqual({}, db.data.load_many_low_level(list(recordings)))

        one = {"data": "one",
               "metadata": {"audio_properties": {"lossless": True}, "version": {"essentia_build_sha": "x"}}}
        two = {"data": "two",
               "metadata": {"audio_properties": {"lossless": True}, "version": {"essentia_build_sha": "x"}}}
        db.data.write_low_level(self.test_mbid, one, gid_types.GID_TYPE_MBID)
        db.data.write_low_level(self.test_mbid_two, two, gid_types.GID_TYPE_MBID)

        recordings = [(self.test_mbid, 0),
                      (self.test_mbid, 1),
                      (self.test_mbid_two, 0),
                      ('ffcc4249-28bb-4c91-9195-a60b21d4fb94', 0)]

        ll_expected = {
            self.test_mbid: {'0': one},
            self.test_mbid_two: {'0': two}
        }

        self.assertEqual(ll_expected, db.data.load_many_low_level(list(recordings)))

    def test_write_load_high_level(self):
        """Writing and loading a dict returns the same data"""
        ll = {"data": "one",
              "metadata": {"audio_properties": {"lossless": True}, "version": {"essentia_build_sha": "x"}}}
        ver = {"hlversion": "123", "models_essentia_git_sha": "v1"}
        hl = {"highlevel": {"model1": {"x": "y"}, "model2": {"a": "b"}},
              "metadata": {"meta": "here",
                           "version": {"highlevel": ver}
                           }
              }

        db.data.add_model("model1", "v1", "show")
        db.data.add_model("model2", "v1", "show")

        build_sha = "test"
        db.data.write_low_level(self.test_mbid, ll, gid_types.GID_TYPE_MBID)
        ll_id = self._get_ll_id_from_mbid(self.test_mbid)[0]
        db.data.write_high_level(self.test_mbid, ll_id, hl, build_sha)

        hl_expected = copy.deepcopy(hl)
        for mname in ["model1", "model2"]:
            hl_expected["highlevel"][mname]["version"] = ver

        self.assertEqual(hl_expected, db.data.load_high_level(self.test_mbid))

    def test_write_high_level_no_data(self):
        # an empty highlevel block should write an entry to the `highlevel` table

        build_sha = "test"
        ll = {"data": "one",
              "metadata": {"audio_properties": {"lossless": True}, "version": {"essentia_build_sha": "x"}}}
        db.data.write_low_level(self.test_mbid, ll, gid_types.GID_TYPE_MBID)
        ll_id = self._get_ll_id_from_mbid(self.test_mbid)[0]
        db.data.write_high_level(self.test_mbid, ll_id, {}, build_sha)

        with self.assertRaises(db.exceptions.NoDataFoundException):
            # Because we have no metadata, load_high_level won't return anything
            db.data.load_high_level(self.test_mbid)

        # However, it should still exist
        with db.engine.connect() as connection:
            result = connection.execute("select id from highlevel where mbid = %s", (self.test_mbid,))
            self.assertEqual(result.rowcount, 1)

    def test_load_high_level_offset(self):
        # If there are two lowlevel items, but only one highlevel, we should raise NoDataFound
        second_data = copy.deepcopy(self.test_lowlevel_data)
        second_data["metadata"]["tags"]["album"] = ["Another album"]

        db.data.write_low_level(self.test_mbid, self.test_lowlevel_data, gid_types.GID_TYPE_MBID)
        db.data.write_low_level(self.test_mbid, second_data, gid_types.GID_TYPE_MBID)
        ll_id1, ll_id2 = self._get_ll_id_from_mbid(self.test_mbid)

        db.data.add_model("model1", "v1", "show")
        db.data.add_model("model2", "v1", "show")

        build_sha = "sha"
        ver = {"hlversion": "123", "models_essentia_git_sha": "v1"}
        hl1 = {"highlevel": {"model1": {"x": "y"}, "model2": {"a": "b"}},
               "metadata": {"meta": "here",
                            "version": {"highlevel": ver}
                            }
               }
        hl2 = {"highlevel": {"model1": {"1": "2"}, "model2": {"3": "3"}},
               "metadata": {"meta": "for hl2",
                            "version": {"highlevel": ver}
                            }
               }
        db.data.write_high_level(self.test_mbid, ll_id1, hl1, build_sha)

        hl1_expected = copy.deepcopy(hl1)
        hl2_expected = copy.deepcopy(hl2)
        for mname in ["model1", "model2"]:
            hl1_expected["highlevel"][mname]["version"] = ver
            hl2_expected["highlevel"][mname]["version"] = ver

        # First highlevel item
        self.assertEqual(hl1_expected, db.data.load_high_level(self.test_mbid))
        self.assertEqual(hl1_expected, db.data.load_high_level(self.test_mbid, offset=0))

        # second has a ll, but no hl => exception
        with self.assertRaises(db.exceptions.NoDataFoundException):
            db.data.load_high_level(self.test_mbid, offset=1)

        # after adding the hl, no error
        db.data.write_high_level(self.test_mbid, ll_id2, hl2, build_sha)
        self.assertEqual(hl2_expected, db.data.load_high_level(self.test_mbid, offset=1))

    def test_load_high_level_offset_reverse(self):
        # If hl are added in a different order to ll, offset should return ll order
        second_data = copy.deepcopy(self.test_lowlevel_data)
        second_data["metadata"]["tags"]["album"] = ["Another album"]

        db.data.write_low_level(self.test_mbid, self.test_lowlevel_data, gid_types.GID_TYPE_MBID)
        db.data.write_low_level(self.test_mbid, second_data, gid_types.GID_TYPE_MBID)
        ll_id1, ll_id2 = self._get_ll_id_from_mbid(self.test_mbid)

        db.data.add_model("model1", "v1", "show")
        db.data.add_model("model2", "v1", "show")

        build_sha = "sha"
        ver = {"hlversion": "123", "models_essentia_git_sha": "v1"}
        hl1 = {"highlevel": {"model1": {"x": "y"}, "model2": {"a": "b"}},
               "metadata": {"meta": "here",
                            "version": {"highlevel": ver}
                            }
               }
        hl2 = {"highlevel": {"model1": {"1": "2"}, "model2": {"3": "3"}},
               "metadata": {"meta": "for hl2",
                            "version": {"highlevel": ver}
                            }
               }
        db.data.write_high_level(self.test_mbid, ll_id2, hl2, build_sha)
        db.data.write_high_level(self.test_mbid, ll_id1, hl1, build_sha)

        hl1_expected = copy.deepcopy(hl1)
        hl2_expected = copy.deepcopy(hl2)
        for mname in ["model1", "model2"]:
            hl1_expected["highlevel"][mname]["version"] = ver
            hl2_expected["highlevel"][mname]["version"] = ver

        self.assertEqual(hl1_expected, db.data.load_high_level(self.test_mbid))
        self.assertEqual(hl2_expected, db.data.load_high_level(self.test_mbid, offset=1))

    def test_load_high_level_uuid_case(self):
        """A query with an upper-case uuid will return the correct data"""

        db.data.write_low_level(self.test_mbid, self.test_lowlevel_data, gid_types.GID_TYPE_MBID)
        ll_id1 = self._get_ll_id_from_mbid(self.test_mbid)[0]

        db.data.add_model("model1", "v1", "show")

        build_sha = "sha"
        ver = {"hlversion": "123", "models_essentia_git_sha": "v1"}
        hl1 = {"highlevel": {"model1": {"x": "y"}},
               "metadata": {"meta": "here",
                            "version": {"highlevel": ver}
                            }
               }
        db.data.write_high_level(self.test_mbid, ll_id1, hl1, build_sha)

        hl1_expected = copy.deepcopy(hl1)
        hl1_expected["highlevel"]["model1"]["version"] = ver

        # upper-case mbid returns correct value
        self.assertEqual(hl1_expected, db.data.load_high_level(self.test_mbid.upper()))

        # load_many
        recordings = [(self.test_mbid.upper(), 0)]

        # Second item skipped
        # The hl are added in a different order to ll, but offset should return ll order
        expected = {self.test_mbid: {'0': hl1_expected}}
        self.assertDictEqual(expected, db.data.load_many_high_level(list(recordings)))

    def test_load_high_level_none(self):
        """If no highlevel data has been calculated, or offset is too high,
        an exception is raised"""

        # no data
        with self.assertRaises(db.exceptions.NoDataFoundException):
            db.data.load_high_level(self.test_mbid, offset=0)

        db.data.write_low_level(self.test_mbid, self.test_lowlevel_data, gid_types.GID_TYPE_MBID)
        ll_id1 = self._get_ll_id_from_mbid(self.test_mbid)[0]

        db.data.add_model("model1", "1.0", "show")
        db.data.add_model("model2", "1.0", "show")

        build_sha = "sha"
        hl1 = {"highlevel": {"model1": {"x": "y"}, "model2": {"a": "b"}},
               "metadata": {"meta": "here",
                            "version": {"highlevel": {"hlversion": "123",
                                                      "models_essentia_git_sha": "v1"}}
                            }
               }
        db.data.write_high_level(self.test_mbid, ll_id1, hl1, build_sha)

        with self.assertRaises(db.exceptions.NoDataFoundException):
            db.data.load_high_level(self.test_mbid, offset=1)

    def test_load_high_level_missing_offset(self):
        """If the highlevel for a submission failed to compute, it doesn't exist
        and a subsequent duplicate submission continues the offsets.

        For example, if for the same mbid we have 3 submissions, -0, -1, -2
        and highlevel for -1 fails to compute, we should still be able to access
        hl offset -2, which is the match to ll-2"""

        first_data = self.test_lowlevel_data
        second_data = copy.deepcopy(first_data)
        second_data["metadata"]["tags"]["album"] = ["Another album"]
        third_data = copy.deepcopy(first_data)
        third_data["metadata"]["tags"]["album"] = ["Final album"]

        db.data.write_low_level(self.test_mbid, first_data, gid_types.GID_TYPE_MBID)
        db.data.write_low_level(self.test_mbid, second_data, gid_types.GID_TYPE_MBID)
        db.data.write_low_level(self.test_mbid, third_data, gid_types.GID_TYPE_MBID)
        ll_id1, ll_id2, ll_id3 = self._get_ll_id_from_mbid(self.test_mbid)

        db.data.add_model("model1", "v1", "show")

        build_sha = "sha"
        ver = {"hlversion": "123", "models_essentia_git_sha": "v1"}
        hl1 = {"highlevel": {"model1": {"x": "y"}},
               "metadata": {"meta": "here",
                            "version": {"highlevel": ver}
                            }
               }
        hl3 = {"highlevel": {"model1": {"1": "2"}},
               "metadata": {"meta": "for hl3",
                            "version": {"highlevel": ver}
                            }
               }
        db.data.write_high_level(self.test_mbid, ll_id1, hl1, build_sha)
        db.data.write_high_level(self.test_mbid, ll_id2, {}, build_sha)
        db.data.write_high_level(self.test_mbid, ll_id3, hl3, build_sha)

        hl1_expected = copy.deepcopy(hl1)
        hl3_expected = copy.deepcopy(hl3)
        hl1_expected["highlevel"]["model1"]["version"] = ver
        hl3_expected["highlevel"]["model1"]["version"] = ver
        self.assertDictEqual(hl1_expected, db.data.load_high_level(self.test_mbid, offset=0))

        with self.assertRaises(db.exceptions.NoDataFoundException):
            db.data.load_high_level(self.test_mbid, offset=1)

        self.assertDictEqual(hl3_expected, db.data.load_high_level(self.test_mbid, offset=2))

    def test_load_many_high_level_skip(self):
        """If two ll items exist but hl fails for second, the second is skipped.

           If one submission hl fails to compute, hl for subsquent submission
           is still retrievable.
        """
        second_data = copy.deepcopy(self.test_lowlevel_data)
        second_data["metadata"]["tags"]["album"] = ["Another album"]

        third_data = copy.deepcopy(self.test_lowlevel_data)
        third_data["metadata"]["tags"]["album"] = ["Yet another album"]

        db.data.write_low_level(self.test_mbid, self.test_lowlevel_data, gid_types.GID_TYPE_MBID)
        db.data.write_low_level(self.test_mbid, second_data, gid_types.GID_TYPE_MBID)
        db.data.write_low_level(self.test_mbid, third_data, gid_types.GID_TYPE_MBID)
        ll_id1, ll_id2, ll_id3 = self._get_ll_id_from_mbid(self.test_mbid)

        db.data.add_model("model1", "v1", "show")
        db.data.add_model("model2", "v1", "show")

        build_sha = "sha"
        ver = {"hlversion": "123", "models_essentia_git_sha": "v1"}
        hl1 = {"highlevel": {"model1": {"x": "y"}, "model2": {"a": "b"}},
               "metadata": {"meta": "here",
                            "version": {"highlevel": ver}
                            }
               }
        hl2 = {"highlevel": {"model1": {"1": "2"}, "model2": {"3": "3"}},
               "metadata": {"meta": "for hl2",
                            "version": {"highlevel": ver}
                            }
               }
        hl3 = {"highlevel": {"model1": {"3": "4"}, "model2": {"4": "4"}},
               "metadata": {"meta": "for hl3",
                            "version": {"highlevel": ver}
                            }
               }
        db.data.write_high_level(self.test_mbid, ll_id1, hl1, build_sha)
        db.data.write_high_level(self.test_mbid, ll_id3, hl3, build_sha)

        hl1_expected = copy.deepcopy(hl1)
        hl2_expected = copy.deepcopy(hl2)
        hl3_expected = copy.deepcopy(hl3)
        for mname in ["model1", "model2"]:
            hl1_expected["highlevel"][mname]["version"] = ver
            hl2_expected["highlevel"][mname]["version"] = ver
            hl3_expected["highlevel"][mname]["version"] = ver

        recordings = [(self.test_mbid, 0),
                      (self.test_mbid, 1),
                      (self.test_mbid, 2)]

        # Second item skipped
        # The hl are added in a different order to ll, but offset should return ll order
        expected = {self.test_mbid: {'0': hl1_expected, '2': hl3_expected}}
        self.assertDictEqual(expected, db.data.load_many_high_level(list(recordings)))

        # After adding the hl, the second is included
        db.data.write_high_level(self.test_mbid, ll_id2, hl2, build_sha)
        expected = {self.test_mbid: {'0': hl1_expected, '1': hl2_expected, '2': hl3_expected}}

        self.assertDictEqual(expected, db.data.load_many_high_level(list(recordings)))

    def test_load_many_high_level_offset(self):
        # If no hl data is found, empty dictionary is returned
        recordings = [(self.test_mbid, 0),
                      (self.test_mbid_two, 0)]

        self.assertEqual({}, db.data.load_many_high_level(list(recordings)))

        # If an offset doesn't exist or recording doesn't exist, it is skipped.
        db.data.write_low_level(self.test_mbid, self.test_lowlevel_data, gid_types.GID_TYPE_MBID)
        db.data.write_low_level(self.test_mbid_two, self.test_lowlevel_data_two, gid_types.GID_TYPE_MBID)
        ll_id1 = self._get_ll_id_from_mbid(self.test_mbid)[0]
        ll_id2 = self._get_ll_id_from_mbid(self.test_mbid_two)[0]

        db.data.add_model("model1", "v1", "show")
        db.data.add_model("model2", "v1", "show")

        build_sha = "sha"
        ver = {"hlversion": "123", "models_essentia_git_sha": "v1"}
        hl1 = {"highlevel": {"model1": {"x": "y"}, "model2": {"a": "b"}},
               "metadata": {"meta": "here",
                            "version": {"highlevel": ver}
                            }
               }
        hl2 = {"highlevel": {"model1": {"1": "2"}, "model2": {"3": "3"}},
               "metadata": {"meta": "for hl2",
                            "version": {"highlevel": ver}
                            }
               }

        db.data.write_high_level(self.test_mbid, ll_id1, hl1, build_sha)
        db.data.write_high_level(self.test_mbid_two, ll_id2, hl2, build_sha)

        hl1_expected = copy.deepcopy(hl1)
        hl2_expected = copy.deepcopy(hl2)
        for mname in ["model1", "model2"]:
            hl1_expected["highlevel"][mname]["version"] = ver
            hl2_expected["highlevel"][mname]["version"] = ver

        recordings = [(self.test_mbid, 0),
                      (self.test_mbid, 3),
                      (self.test_mbid_two, 0),
                      ("ffcc4249-28bb-4c91-9195-a60b31d4fb94", 0)]

        expected = {
            self.test_mbid: {'0': hl1_expected},
            self.test_mbid_two: {'0': hl2_expected}
        }
        self.assertEqual(expected, db.data.load_many_high_level(list(recordings)))

    def test_load_high_level_map_class_names(self):
        recordings = [(self.test_mbid, 0)]

        # If an offset doesn't exist or recording doesn't exist, it is skipped.
        db.data.write_low_level(self.test_mbid, self.test_lowlevel_data, gid_types.GID_TYPE_MBID)
        ll_id1 = self._get_ll_id_from_mbid(self.test_mbid)[0]

        db.data.add_model("model1", "v1", "show")

        build_sha = "sha"
        ver = {"hlversion": "123", "models_essentia_git_sha": "v1"}
        hl1 = {"highlevel": {"model1": {"all": {"one": 0.4, "two": 0.6}, "probability": 0.6, "value": "two"}},
               "metadata": {"meta": "here",
                            "version": {"highlevel": ver}
                            }
               }
        db.data.write_high_level(self.test_mbid, ll_id1, hl1, build_sha)

        hl1_expected = copy.deepcopy(hl1)
        hl1_expected["highlevel"]["model1"]["version"] = ver

        expected = {
            self.test_mbid: {'0': hl1_expected},
        }
        # If we set map_classes, but there is no mapping, the results are the same as the original version
        self.assertEqual(expected, db.data.load_many_high_level(list(recordings), map_classes=True))

        # We have only one model, so for testing we just unconditionally set the mapping
        with db.engine.connect() as connection:
            connection.execute(
                sqlalchemy.text("""UPDATE model set class_mapping = '{"one": "Class One", "two": "Class Two"}'::jsonb""")
            )

        # Now with the mapping, the values in the expected values have been changed
        hl1_expected = copy.deepcopy(hl1)
        hl1_expected["highlevel"]["model1"]["version"] = ver
        hl1_expected["highlevel"]["model1"]["value"] = "Class Two"
        hl1_expected["highlevel"]["model1"]["all"] = {"Class One": 0.4, "Class Two": 0.6}

        expected = {
            self.test_mbid: {'0': hl1_expected},
        }
        self.assertEqual(expected, db.data.load_many_high_level(list(recordings), map_classes=True))

    def test_load_many_individual_features(self):
        """Lowlevel data returned matches (mbid, offset) pairs. Only returns features that
        are specified, with lowlevel structure maintained.
        """
        second_data = copy.deepcopy(self.test_lowlevel_data)
        second_data["metadata"]["tags"]["album"] = ["Another album"]

        db.data.write_low_level(self.test_mbid, self.test_lowlevel_data, gid_types.GID_TYPE_MBID)
        db.data.write_low_level(self.test_mbid, second_data, gid_types.GID_TYPE_MBID)
        db.data.write_low_level(self.test_mbid_two, self.test_lowlevel_data_two, gid_types.GID_TYPE_MBID)

        # If no data exists for an (mbid, offset) pair, it is skipped
        recordings = [(self.test_mbid, 0),
                      (self.test_mbid, 1),
                      (self.test_mbid, 2),
                      (self.test_mbid_two, 0)]

        features = [("llj.data->'lowlevel'->'average_loudness'", "lowlevel.average_loudness", None),
                    ("llj.data->'lowlevel'->'dynamic_complexity'", "lowlevel.dynamic_complexity", None),
                    ("llj.data->'metadata'->'audio_properties'->'replay_gain'", "metadata.audio_properties.replay_gain", None),
                    ("llj.data->'metadata'->'tags'", "metadata.tags", {}),
                    ("llj.data->'rhythm'->'beats_loudness'->'mean'", "rhythm.beats_loudness.mean", None),
                    ("llj.data->'rhythm'->'bpm_histogram_second_peak_bpm'->'mean'", "rhythm.bpm_histogram_second_peak_bpm.mean", None),
                    ("llj.data->'tonal'->'key_key'", "tonal.key_key", None)]

        expected = json.loads(open(os.path.join(DB_TEST_DATA_PATH, "lowlevel_select_features_response.json")).read())
        self.assertEqual(expected, db.data.load_many_individual_features(list(recordings), features))

    def test_load_many_individual_features_none(self):
        """If there is no data found for any of the specified recordings,
        an empty dictionary is returned. If there is no data for a feature,
        it is returned with the specified default value."""
        # No data written for the recordings specified
        recordings = [(self.test_mbid, 0),
                      (self.test_mbid_two, 0)]

        features = [("llj.data->'lowlevel'->'average_loudness'", "lowlevel.average_loudness", None),
                    ("llj.data->'lowlevel'->'dynamic_complexity'", "lowlevel.dynamic_complexity", None),
                    ("llj.data->'metadata'->'audio_properties'->'replay_gain'", "metadata.audio_properties.replay_gain", None),
                    ("llj.data->'metadata'->'tags'", "metadata.tags", {}),
                    ("llj.data->'rhythm'->'beats_loudness'->'mean'", "rhythm.beats_loudness.mean", None),
                    ("llj.data->'rhythm'->'bpm_histogram_second_peak_bpm'->'mean'", "rhythm.beats_loudness.mean", None),
                    ("llj.data->'tonal'->'key_key'", "tonal.key_key", None)]

        expected = {}
        self.assertEqual(expected, db.data.load_many_individual_features(list(recordings), features))

        # No existing data for a feature
        altered_data = copy.deepcopy(self.test_lowlevel_data)
        del altered_data["lowlevel"]["average_loudness"]
        del altered_data["metadata"]["tags"]
        db.data.write_low_level(self.test_mbid, altered_data, gid_types.GID_TYPE_MBID)

        recordings = [(self.test_mbid, 0)]

        features = [("llj.data->'lowlevel'->'average_loudness'", "lowlevel.average_loudness", None),
                    ("llj.data->'metadata'->'audio_properties'->'replay_gain'", "metadata.audio_properties.replay_gain", None),
                    ("llj.data->'metadata'->'tags'", "metadata.tags", {})]

        expected = {"0dad432b-16cc-4bf0-8961-fd31d124b01b": {"0": {"lowlevel": {"average_loudness": None},
                                                                   "metadata": {"audio_properties": {
                                                                       "replay_gain": -9.43081283569},
                                                                       "tags": {}}}}}

        self.assertEqual(expected, db.data.load_many_individual_features(list(recordings), features))

    def test_build_feature_string(self):
        """Check the string returned follows the pattern:
           "<feature_path_1> AS <alias>, <feature_path_2> AS <alias>"
        """
        # If features is empty, empty string should be returned
        features = []
        self.assertEqual("", db.data.build_feature_string(features))

        features = [("llj.data->'lowlevel'->'average_loudness'", "lowlevel.average_loudness", None),
                    ("llj.data->'lowlevel'->'dynamic_complexity'", "lowlevel.dynamic_complexity", None)]
        expected_string = """llj.data->'lowlevel'->'average_loudness' AS \"lowlevel.average_loudness\", llj.data->'lowlevel'->'dynamic_complexity' AS \"lowlevel.dynamic_complexity\""""
        self.assertEqual(expected_string, db.data.build_feature_string(features))

    def test_bulk_get_feature_recordings(self):
        # If all (MBID, offsets) are not present, empty array is returned
        feature_string = """llj.data->'lowlevel'->'average_loudness' AS \"lowlevel.average_loudness\",
                            llj.data->'metadata'->'tags' AS \"metadata.tags\""""
        recordings = [(self.test_mbid, 0)]
        self.assertEqual([], db.data.bulk_get_recording_features(recordings, feature_string))

        # If an (MBID, offset) combination is not present in the database, it is skipped
        # Only the individual features specified should be returned from query
        recordings = [(self.test_mbid, 0), (self.test_mbid, 10)]
        db.data.submit_low_level_data(self.test_mbid, self.test_lowlevel_data, gid_types.GID_TYPE_MBID)

        # Whole groups of features (i.e. higher order keys from the lowlevel document)
        # can be returned as dicts as well
        expected_rows = [(self.test_mbid,
                          '0',
                          0.048737552017,
                          {"acoustid_id": ["25343079-d20f-4827-9e83-840e278a67ff"],
                           "album": ["Journey"],
                           "albumartist": ["Austin Wintory"],
                           "albumartistsort": ["Wintory, Austin"],
                           "artist": ["Austin Wintory"],
                           "artistsort": ["Wintory, Austin"],
                           "artistwebpage": ["http://austinwintory.com/"],
                           "date": ["2012"],
                           "discnumber": ["1/1"],
                           "file_name": "01 Nascence.mp3",
                           "media": ["Digital Media"],
                           "musicbrainz album release country": ["XW"],
                           "musicbrainz album status": ["official"],
                           "musicbrainz album type": ["album/soundtrack"],
                           "musicbrainz_albumartistid": ["78f15956-c5e1-46d6-a46b-fa6f46681ec8"],
                           "musicbrainz_albumid": ["1f3abcda-15a7-4465-92c6-9926cdc4f247"],
                           "musicbrainz_artistid": ["78f15956-c5e1-46d6-a46b-fa6f46681ec8"],
                           "musicbrainz_recordingid": ["0dad432b-16cc-4bf0-8961-fd31d124b01b"],
                           "musicbrainz_releasegroupid": ["d1850227-c7c7-42c8-b469-6e99023412de"],
                           "originaldate": ["2012"],
                           "script": ["Latn"],
                           "title": ["Nascence"],
                           "tracknumber": ["1/18"]}
                          )]
        self.assertEqual(expected_rows, db.data.bulk_get_recording_features(recordings, feature_string))

    def test_parse_features_row_missing_feature(self):
        """If a feature is missing from feature list or is not
        present in lowlevel row, default type will be used."""
        row = {"gid": self.test_mbid,
               "submission_offset": 0,
               "lowlevel.average_loudness": 0.048737552017,
               "rhythm.bpm": None}
        features = [("llj.data->'lowlevel'->'average_loudness'", "lowlevel.average_loudness", None),
                    ("llj.data->'metadata'->'tags'", "metadata.tags", {}),
                    ("llj.data->'rhythm'->'bpm'", "rhythm.bpm", None)]

        # Row data is reconstructed to mirror lowlevel document structure
        expected_dict = {"lowlevel": {"average_loudness": 0.048737552017},
                         "metadata": {"tags": {}},
                         "rhythm": {"bpm": None}}
        self.assertEqual(expected_dict, db.data.parse_features_row(row, features))

    def test_count_lowlevel(self):
        db.data.submit_low_level_data(self.test_mbid, self.test_lowlevel_data, gid_types.GID_TYPE_MBID)
        self.assertEqual(1, db.data.count_lowlevel(self.test_mbid))
        # Exact same data is deduplicated
        db.data.submit_low_level_data(self.test_mbid, self.test_lowlevel_data, gid_types.GID_TYPE_MBID)
        self.assertEqual(1, db.data.count_lowlevel(self.test_mbid))

        # make a copy of the data and change it
        second_data = copy.deepcopy(self.test_lowlevel_data)
        second_data["metadata"]["tags"]["album"] = ["Another album"]
        db.data.submit_low_level_data(self.test_mbid, second_data, gid_types.GID_TYPE_MBID)
        self.assertEqual(2, db.data.count_lowlevel(self.test_mbid))

    def test_add_get_model(self):
        self.assertIsNone(db.data._get_model_id("modelname", "v1"))

        modelid = db.data.add_model("modelname", "v1")
        get_id = db.data._get_model_id("modelname", "v1")
        self.assertEqual(modelid, get_id)

    def test_get_failed_highlevel_submissions(self):
        hl = {"highlevel": {"model1": {"x": "y"}, "model2": {"a": "b"}},
              "metadata": {}
              }
        build_sha = "test"
        db.data.submit_low_level_data(
            self.test_mbid, self.test_lowlevel_data, gid_types.GID_TYPE_MBID)
        ll_id = self._get_ll_id_from_mbid(self.test_mbid)[0]
        db.data.write_high_level(self.test_mbid, ll_id, hl, build_sha)

        rows = db.data.get_failed_highlevel_submissions()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["gid"], self.test_mbid)

    def test_get_active_models(self):
        models = db.data.get_active_models()
        self.assertEqual(len(models), 0)
        db.data.add_model("new_model", "v1", db.data.STATUS_SHOW)

        models = db.data.get_active_models()
        self.assertEqual(len(models), 1)

        # Adding a hidden model doesn't affect the result
        db.data.add_model("hidden_test", "v1", db.data.STATUS_HIDDEN)
        models = db.data.get_active_models()
        self.assertEqual(len(models), 1)

    def test_get_summary_data(self):
        pass


    def test_load_new_recordings_from_lowlevel(self):
        """Two mbids are inserted into lowlevel table and then fetch a list of newly added mbids
        and then check if both the lists contain similar items"""
        recording_mbids = [uuid.UUID('ceec2751-44fe-44ff-b281-de00df9117d8'), uuid.UUID('575519b3-c06b-4157-b172-5d7ca80a8382')]
        one = {"data": "one", "metadata": {"audio_properties": {"lossless": True}, "version": {"essentia_build_sha": "x"}}}
        two = {"data": "two", "metadata": {"audio_properties": {"lossless": True}, "version": {"essentia_build_sha": "x"}}}
        db.data.write_low_level(recording_mbids[0], one, gid_types.GID_TYPE_MBID)
        db.data.write_low_level(recording_mbids[1], two, gid_types.GID_TYPE_MBID)

        self.assertEqual(recording_mbids, db.data.get_new_recordings_from_lowlevel())


class DataUtilTestCase(AcousticbrainzTestCase):
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

    def test_map_highlevel_class_names(self):
        highlevel = {
          "all": {
            "blu": 0.0626613423228,
            "cla": 0.0348169617355,
            "cou": 0.104475811124,
            "dis": 0.0784321576357,
            "hip": 0.15692435205,
            "jaz": 0.313974827528,
            "met": 0.0448166541755,
            "pop": 0.0627359300852,
            "reg": 0.0627360641956,
            "roc": 0.0784258767962
          },
          "probability": 0.313974827528,
          "value": "jaz",
          "version": {
            "essentia": "2.1-beta1",
            "essentia_build_sha": "8e24b98b71ad84f3024c7541412f02124a26d327",
            "essentia_git_sha": "v2.1_beta1-228-g260734a",
            "extractor": "music 1.0",
            "gaia": "2.4-dev",
            "gaia_git_sha": "857329b",
            "models_essentia_git_sha": "v2.1_beta1"
          }
        }
        mapping = {
            "blu": "Blues",
            "cla": "Classical",
            "cou": "Country",
            "dis": "Disco",
            "hip": "Hiphop",
            "jaz": "Jazz",
            "met": "Metal",
            "pop": "Pop",
            "reg": "Reggae",
            "roc": "Rock"
        }

        mapped = db.data.map_highlevel_class_names(highlevel, mapping)

        self.assertEqual(mapped["value"], "Jazz")
        self.assertItemsEqual(mapped["all"], ["Blues", "Classical", "Country", "Disco", "Hiphop",
                                              "Jazz", "Metal", "Pop", "Reggae", "Rock"])
