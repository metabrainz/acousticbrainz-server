import db
import db.data
import unittest
import json
import os

# Configuration
import sys
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), ".."))
import config

ADMIN_SQL_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', 'admin', 'sql')
TEST_DATA_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'test_data')


class DatabaseTestCase(unittest.TestCase):

    def setUp(self):
        db.init_db_engine(config.SQLALCHEMY_TEST_URI)
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

    def drop_types(self):
        with db.engine.connect() as connection:
            connection.execute('DROP TYPE IF EXISTS eval_job_status CASCADE;')
            connection.execute('DROP TYPE IF EXISTS model_status CASCADE;')
            connection.execute('DROP TYPE IF EXISTS version_type CASCADE;')

    def data_filename(self, mbid):
        """ Get the expected filename of a test datafile given its mbid """
        return os.path.join(TEST_DATA_PATH, mbid + '.json')

    def load_low_level_data(self, mbid):
        """Loads low-level data from JSON file in `test_data` directory into
        the database.
        """
        with open(self.data_filename(mbid)) as json_file:
            db.data.submit_low_level_data(mbid, json.loads(json_file.read()))

