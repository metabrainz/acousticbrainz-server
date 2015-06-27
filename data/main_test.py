from data.testing import DataTestCase, TEST_DATA_PATH
from data import main
import os.path
import json


class DataMainTestCase(DataTestCase):

    def setUp(self):
        super(DataMainTestCase, self).setUp()
        self.test_mbid = "0dad432b-16cc-4bf0-8961-fd31d124b01b"
        self.test_lowlevel_data_json = open(os.path.join(TEST_DATA_PATH, self.test_mbid + '.json')).read()
        self.test_lowlevel_data = json.loads(self.test_lowlevel_data_json)

    def test_submit_low_level_data(self):
        main.submit_low_level_data(self.test_mbid, self.test_lowlevel_data)
        self.assertIsNotNone(main.load_low_level(self.test_mbid))
