import copy
import json
import os.path
import unittest

import mock

import db.similarity
import db.exceptions
from db.testing import DatabaseTestCase, TEST_DATA_PATH, gid_types
import similarity.metrics


class SimilarityDBTestCase(DatabaseTestCase):

    def setUp(self):
        super(SimilarityDBTestCase, self).setUp()
        self.test_mbid = "0dad432b-16cc-4bf0-8961-fd31d124b01b"
        self.test_lowlevel_data_json = open(os.path.join(TEST_DATA_PATH, self.test_mbid + '.json')).read()
        self.test_lowlevel_data = json.loads(self.test_lowlevel_data_json)

        self.test_mbid_two = 'e8afe383-1478-497e-90b1-7885c7f37f6e'
        self.test_lowlevel_data_json_two = open(os.path.join(TEST_DATA_PATH, self.test_mbid_two + '.json')).read()
        self.test_lowlevel_data_two = json.loads(self.test_lowlevel_data_json_two)

    def test_count_similarity(self):
        # Write lowlevel then submit similarity
        db.data.submit_low_level_data(self.test_mbid, self.test_lowlevel_data, gid_types.GID_TYPE_MBID)
        db.similarity.submit_similarity_by_mbid(self.test_mbid, 0)
        self.assertEqual(1, db.similarity.count_similarity())
        # Submit exact same data, no change
        db.similarity.submit_similarity_by_mbid(self.test_mbid, 0)
        self.assertEqual(1, db.similarity.count_similarity())

        # make a copy of the data and change it
        second_data = copy.deepcopy(self.test_lowlevel_data)
        second_data["metadata"]["tags"]["album"] = ["Another album"]
        db.data.submit_low_level_data(self.test_mbid, second_data, gid_types.GID_TYPE_MBID)
        db.similarity.submit_similarity_by_mbid(self.test_mbid, 1)
        self.assertEqual(2, db.similarity.count_similarity())

    @unittest.skip
    @mock.patch("db.similarity.get_metrics_data")
    @mock.patch("db.similarity.insert_similarity")
    def test_submit_similarity_by_id(self, insert_similarity, get_metrics_data):
        """If highlevel and lowlevel data exists for id, check that insert_similarity 
        is called with the specified id, as well as all metrics and their vectors, for
        which none are empty (`isnan` must be False).

        If highlevel does not exist, vectors for highlevel metrics should have `isnan`
        as True, and be of the form [None, ..., None]

        If highlevel does not exist for a model, the corresponding metric should have
        vector with `isnan` as True and be of the form [None, ..., None]
        """
        db.data.write_low_level(self.test_mbid, self.test_lowlevel_data, gid_types.GID_TYPE_MBID)
        ll_id1 = db.data.get_lowlevel_id(self.test_mbid, 0)

        # Add all models required for similarity
        for name, version, status in similarity.metrics.BASE_MODELS:
            db.data.add_model(name, version, status)

        build_sha = "sha"
        hl = json.loads(open(os.path.join(TEST_DATA_PATH, self.test_mbid + '_highlevel.json')).read())
        db.data.write_high_level(self.test_mbid, ll_id1, hl, build_sha)

        id = db.data.get_lowlevel_id(self.test_mbid, 0)
        db.similarity.submit_similarity_by_id(id)

        vectors_info = [('mfccs', [0.988367855549, 0.0248921476305, 0.965500116348], False),
        ('mfccsw', [0.690790155245792, 0.723055296236391], False),
        ('gfccs', [1.77530184126608, 0.944378506164033, -0.873178308877563, -0.101202090509241, -0.413312439649938, -0.435524397547275, -0.226877337223418, -0.442540751135574, -0.554835175091169, -0.538162986673237, -0.278829360964993, 0.234642688200534], False),
        ('gfccsw', [0.00617602840066, 0.195983037353, 0.0784998983145, 0.0032169369515, 0.00680347532034, 0.663908660412, 0.0344416685402, 0.010970310308], False),
        ('key', [2.0131596472614, 0.416072194918468, -0.82365613396016, -0.405594718040805, 0.0598732233828964, -1.17039410061734, -0.225057107206926, -0.654149626932212, -0.783917722845553, -1.13555180528494, -0.283614006958337, 0.487294088725762], False),
        ('bpm', [0.154698759317, 0.311486542225, 0.0707420706749, 0.0773398503661, 0.0344257615507, 0.0618693865836, 0.0442127361894, 0.0775808021426, 0.0620644688606, 0.10557962954], False),
        ('onsetrate', [0.0581060945988, 0.953247070312, 0.0500397793949, 0.995198726654, 0.0156338009983], False),
        ('moods', [0.5, 0.866025403784439], False),
        ('instruments', [0.00316655938514, 0.00568170007318, 0.114020898938, 0.0338333025575, 0.509120285511, 0.0465195141733, 0.0925819277763, 0.0783302634954, 0.116745553911], False),
        ('dortmund', [1.48801184199116, 0.963673980092963, -1.23671130644121, -0.326172454869213, -1.68831072231553, -1.07566350679267, -1.09876131175972, -0.470538635183069, -1.80834351480784, -2.70053705964867, -1.9702729220569, -0.586094990594924], False),
        ('rosamerica', [0.720150073189895, 0.693818327867309], False),
        ('tzanetakis', [1.30118269347339, 1.08436025250102, -0.439034532349894, 0.177506236399918, -1.49602752970215, -0.737996348117037, -0.608238495163597, -0.0994916172403261, -1.11919342422039, -1.58447220399166, -1.08427389857258, -0.252746253303151], False)]

        with db.engine.connect() as connection:
            # expected_metrics = []
            # for name in similarity.metrics.BASE_METRICS:
            #     metric_cls = similarity.metrics.BASE_METRICS[name]
            #     metric = metric_cls(connection)
            #     expected_metrics.append(metric)

            # get_metrics_data.assert_called_with(id, expected_metrics)
            insert_similarity.assert_called_with(connection, id, vectors_info)

    @unittest.skip
    @mock.patch("db.similarity.get_metrics_data")
    @mock.patch("db.similarity.insert_similarity")
    def test_submit_similarity_by_id_metrics_none(self, insert_similarity, get_metrics_data):
        """If some data does not exist, vectors for those metrics should have `isnan`
        as True, and be of the form [None, ..., None]. E.g. if highlevel is not written.
        """
        db.data.write_low_level(self.test_mbid, self.test_lowlevel_data, gid_types.GID_TYPE_MBID)

        id = db.data.get_lowlevel_id(self.test_mbid, 0)
        db.similarity.submit_similarity_by_id(id)

        vectors_info = [('mfccs', [0.988367855549, 0.0248921476305, 0.965500116348], False),
        ('mfccsw', [0.690790155245792, 0.723055296236391], False),
        ('gfccs', [1.77530184126608, 0.944378506164033, -0.873178308877563, -0.101202090509241, -0.413312439649938, -0.435524397547275, -0.226877337223418, -0.442540751135574, -0.554835175091169, -0.538162986673237, -0.278829360964993, 0.234642688200534], False),
        ('gfccsw', [0.00617602840066, 0.195983037353, 0.0784998983145, 0.0032169369515, 0.00680347532034, 0.663908660412, 0.0344416685402, 0.010970310308], False),
        ('key', [2.0131596472614, 0.416072194918468, -0.82365613396016, -0.405594718040805, 0.0598732233828964, -1.17039410061734, -0.225057107206926, -0.654149626932212, -0.783917722845553, -1.13555180528494, -0.283614006958337, 0.487294088725762], False),
        ('bpm', [0.154698759317, 0.311486542225, 0.0707420706749, 0.0773398503661, 0.0344257615507, 0.0618693865836, 0.0442127361894, 0.0775808021426, 0.0620644688606, 0.10557962954], False),
        ('onsetrate', [0.0581060945988, 0.953247070312, 0.0500397793949, 0.995198726654, 0.0156338009983], False),
        ('moods', [None, None], True),
        ('instruments', [None, None, None, None, None, None, None, None, None], True),
        ('dortmund', [None, None, None, None, None, None, None, None, None, None, None, None], True),
        ('rosamerica', [None, None], True),
        ('tzanetakis', [None, None, None, None, None, None, None, None, None, None, None, None], True)]
        with db.engine.connect() as connection:
            insert_similarity.assert_called_with(connection, id, vectors_info)

    def test_submit_similarity_by_id_none(self):
        """If id cannot be cast as an integer, a ValueError should be raised.

        If lowlevel is not submitted, a NoDataFoundException should be raised.
        """
        id = 'test'
        with self.assertRaises(db.exceptions.BadDataException):
            db.similarity.submit_similarity_by_id(id)

        id = 100
        with self.assertRaises(db.exceptions.NoDataFoundException):
            db.similarity.submit_similarity_by_id(100)

    def test_submit_similarity_by_mbid_none(self):
        # If no submission exists, NoDataFoundException should be raised.
        with self.assertRaises(db.exceptions.NoDataFoundException):
            db.similarity.submit_similarity_by_mbid(self.test_mbid, 0)

    # Not sure that I need to test get_metrics_data?
    # Not sure how to test add_metrics or insert_similarity
    # @mock.patch("db.similarity.submit_similarity_by_id")
    # def test_submit_similarity_by_mbid(self, submit_similarity_by_id):
    #     """If the given (MBID, offset) combination exists, the lowlevel.id
    #     should be retrieved and passed to submit_similarity_by_id.
    #     """
    #     submit_similarity_by_id.assert_called_with()
    #     # Upper case MBID
    #     submit_similarity_by_id.assert_called_with()

    # def test_submit_similarity_by_mbid_none(self):
    #     """If the given (MBID, offset) combination does not exist, a
    #     NoDataFoundException should be raised.
    #     """
