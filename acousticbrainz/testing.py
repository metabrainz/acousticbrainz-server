from flask_testing import TestCase
from acousticbrainz import create_app
from acousticbrainz.data import submit_low_level_data
import psycopg2
import json
import os


class FlaskTestCase(TestCase):

    def create_app(self):
        app = create_app()
        app.config['TESTING'] = True
        app.config['PG_CONNECT'] = app.config['PG_CONNECT_TEST']
        return app

    def setUp(self):
        pass

    def tearDown(self):
        self.truncate_all()

    def truncate_all(self):
        conn = psycopg2.connect(self.app.config["PG_CONNECT"])
        cur = conn.cursor()
        cur.execute("TRUNCATE highlevel_json CASCADE;")
        cur.execute("TRUNCATE highlevel CASCADE;")
        cur.execute("TRUNCATE lowlevel CASCADE;")
        cur.execute("TRUNCATE statistics CASCADE;")
        cur.execute("TRUNCATE incremental_dumps CASCADE;")
        conn.commit()
        cur.close()
        conn.close()

    def load_low_level_data(self, mbid):
        """Loads low-level data from JSON file in `acousticbrainz/test_data`
        directory into the database.
        """
        with open(os.path.join('acousticbrainz', 'test_data', mbid + '.json')) as json_file:
            submit_low_level_data(mbid, json.loads(json_file.read()))
