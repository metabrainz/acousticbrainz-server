from flask_testing import TestCase
from acousticbrainz import create_app
from acousticbrainz import data
from acousticbrainz.data.data import submit_low_level_data
import json
import os


TEST_DATA_PATH = os.path.join('acousticbrainz', 'data', 'test_data')


class ServerTestCase(TestCase):

    def create_app(self):
        app = create_app()
        app.config['TESTING'] = True
        data.init_connection(app.config['PG_CONNECT_TEST'])
        return app

    def setUp(self):
        self.reset_db()

    def tearDown(self):
        pass

    def reset_db(self):
        self.drop_tables()
        self.init_db()

    def init_db(self):
        data.run_sql_script(os.path.join('admin', 'sql', 'create_tables.sql'))
        data.run_sql_script(os.path.join('admin', 'sql', 'create_primary_keys.sql'))
        data.run_sql_script(os.path.join('admin', 'sql', 'create_foreign_keys.sql'))
        data.run_sql_script(os.path.join('admin', 'sql', 'create_indexes.sql'))

    def drop_tables(self):
        with data.create_cursor() as cursor:
            # TODO(roman): See if there's a better way to drop all tables.
            cursor.execute('DROP TABLE IF EXISTS highlevel_json       CASCADE;')
            cursor.execute('DROP TABLE IF EXISTS highlevel            CASCADE;')
            cursor.execute('DROP TABLE IF EXISTS lowlevel             CASCADE;')
            cursor.execute('DROP TABLE IF EXISTS statistics           CASCADE;')
            cursor.execute('DROP TABLE IF EXISTS incremental_dumps    CASCADE;')
            cursor.execute('DROP TABLE IF EXISTS dataset_class_member CASCADE;')
            cursor.execute('DROP TABLE IF EXISTS dataset_class        CASCADE;')
            cursor.execute('DROP TABLE IF EXISTS dataset              CASCADE;')
            cursor.execute('DROP TABLE IF EXISTS "user"               CASCADE;')
        data.commit()

    def load_low_level_data(self, mbid):
        """Loads low-level data from JSON file in `acousticbrainz/data/test_data`
        directory into the database.
        """
        with open(os.path.join(TEST_DATA_PATH, mbid + '.json')) as json_file:
            submit_low_level_data(mbid, json.loads(json_file.read()))

    def temporary_login(self, user_id):
        with self.client.session_transaction() as session:
            session['user_id'] = user_id
            session['_fresh'] = True

