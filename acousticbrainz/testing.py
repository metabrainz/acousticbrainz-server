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
        pass

    def tearDown(self):
        self.truncate_all()

    def truncate_all(self):
        from acousticbrainz.data import connection
        with connection.cursor() as cursor:
            cursor.execute('TRUNCATE highlevel_json    RESTART IDENTITY CASCADE;')
            cursor.execute('TRUNCATE highlevel         RESTART IDENTITY CASCADE;')
            cursor.execute('TRUNCATE lowlevel          RESTART IDENTITY CASCADE;')
            cursor.execute('TRUNCATE statistics        RESTART IDENTITY CASCADE;')
            cursor.execute('TRUNCATE incremental_dumps RESTART IDENTITY CASCADE;')
            cursor.execute('TRUNCATE "user"            RESTART IDENTITY CASCADE;')
            cursor.execute('TRUNCATE dataset           RESTART IDENTITY CASCADE;')
            cursor.execute('TRUNCATE class             RESTART IDENTITY CASCADE;')
        connection.commit()

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

