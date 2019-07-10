import db
import db.data
import json
import os
import random
from db import gid_types

from webserver import create_app

from flask_testing import TestCase


ADMIN_SQL_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', 'admin', 'sql')
TEST_DATA_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'test_data')


class DatabaseTestCase(TestCase):

    @staticmethod
    def create_app():
        app = create_app()
        app.config['WTF_CSRF_ENABLED'] = False
        return app

    def setUp(self):
        self.reset_db()

    def tearDown(self):
        pass

    def reset_db(self):
        self.drop_tables()
        self.drop_types()
        self.init_db()

    def init_db(self):
        db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'create_types.sql'))
        db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'create_tables.sql'))
        db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'create_primary_keys.sql'))
        db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'create_foreign_keys.sql'))
        db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'create_indexes.sql'))
        db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'populate_tables.sql'))

    def drop_tables(self):
        db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'drop_tables.sql'))

    def drop_types(self):
        db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'drop_types.sql'))

    def data_filename(self, mbid):
        """ Get the expected filename of a test datafile given its mbid """
        return os.path.join(TEST_DATA_PATH, mbid + '.json')

    def load_low_level_data(self, mbid):
        """Loads low-level data from JSON file in `test_data` directory into
        the database.
        """
        with open(self.data_filename(mbid)) as json_file:
            db.data.submit_low_level_data(mbid, json.loads(json_file.read()), gid_types.GID_TYPE_MBID)

    def submit_fake_low_level_data(self, mbid):
        """Generate a minimal dataset to be submitted in tests for a given
        MBID. Several calls to this function generate distinct entries by using
        a random value for the 'average_loudness' field"""
        db.data.submit_low_level_data(
            mbid,
            {"lowlevel": {"average_loudness": random.random()},
             "metadata": {"audio_properties": {"length": None,
                                               "bit_rate": None,
                                               "codec": None,
                                               "lossless": True},
                          "tags": {"file_name": "fake",
                                   "musicbrainz_recordingid": [mbid]},
                          "version": {"essentia": None,
                                      "essentia_build_sha": "",
                                      "essentia_git_sha": None,
                                      "extractor": None}},
             "rhythm": {},
             "tonal": {}
            },
            gid_types.GID_TYPE_MBID)
