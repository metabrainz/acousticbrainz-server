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

    def drop_tables(self):
        with db.engine.connect() as connection:
            # TODO(roman): See if there's a better way to drop all tables.
            connection.execute('DROP TABLE IF EXISTS highlevel_model      CASCADE;')
            connection.execute('DROP TABLE IF EXISTS highlevel_meta       CASCADE;')
            connection.execute('DROP TABLE IF EXISTS highlevel            CASCADE;')
            connection.execute('DROP TABLE IF EXISTS model                CASCADE;')
            connection.execute('DROP TABLE IF EXISTS lowlevel_json        CASCADE;')
            connection.execute('DROP TABLE IF EXISTS lowlevel             CASCADE;')
            connection.execute('DROP TABLE IF EXISTS version              CASCADE;')
            connection.execute('DROP TABLE IF EXISTS statistics           CASCADE;')
            connection.execute('DROP TABLE IF EXISTS incremental_dumps    CASCADE;')
            connection.execute('DROP TABLE IF EXISTS dataset_snapshot     CASCADE;')
            connection.execute('DROP TABLE IF EXISTS dataset_eval_jobs    CASCADE;')
            connection.execute('DROP TABLE IF EXISTS dataset_class_member CASCADE;')
            connection.execute('DROP TABLE IF EXISTS dataset_class        CASCADE;')
            connection.execute('DROP TABLE IF EXISTS dataset              CASCADE;')
            connection.execute('DROP TABLE IF EXISTS dataset_eval_sets    CASCADE;')
            connection.execute('DROP TABLE IF EXISTS "user"               CASCADE;')
            connection.execute('DROP TABLE IF EXISTS api_key              CASCADE;')
            connection.execute('DROP TABLE IF EXISTS challenge            CASCADE;')
            connection.execute('DROP TABLE IF EXISTS dataset_eval_challenge CASCADE;')
            connection.execute('DROP TABLE IF EXISTS feedback               CASCADE;')

    def drop_types(self):
        with db.engine.connect() as connection:
            connection.execute('DROP TYPE IF EXISTS eval_job_status CASCADE;')
            connection.execute('DROP TYPE IF EXISTS model_status CASCADE;')
            connection.execute('DROP TYPE IF EXISTS version_type CASCADE;')
            connection.execute('DROP TYPE IF EXISTS eval_location_type CASCADE;')
            connection.execute('DROP TYPE IF EXISTS gid_type CASCADE;')

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
