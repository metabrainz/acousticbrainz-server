from flask_testing import TestCase
from acousticbrainz import create_app
import psycopg2


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
