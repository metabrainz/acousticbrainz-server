from brainzutils.ratelimit import set_rate_limits

import db
import db.data
import json
import os
import random
from db import gid_types

from webserver import create_app

from flask_testing import TestCase


ADMIN_SQL_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', 'admin', 'sql')
DB_TEST_DATA_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', 'db', 'test_data')
WEB_TEST_DATA_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'views', 'test_data')


class AcousticbrainzTestCase(TestCase):

    def create_app(self):
        app = create_app(debug=False)
        app.config['WTF_CSRF_ENABLED'] = False
        app.config['TESTING'] = True
        return app

    def setUp(self):
        self.reset_db()

        # TODO: https://tickets.metabrainz.org/browse/BU-27
        set_rate_limits(1000, 1000, 10000)

    def temporary_login(self, user_id):
        with self.client.session_transaction() as session:
            session['_user_id'] = user_id
            session['_fresh'] = True

    def reset_db(self):
        self.drop_tables()
        self.drop_types()
        self.init_db()

    def init_db(self):
        db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'create_schema.sql'))
        db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'create_types.sql'))
        db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'create_tables.sql'))
        db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'create_primary_keys.sql'))
        db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'create_foreign_keys.sql'))
        db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'create_indexes.sql'))
        db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'populate_metrics_table.sql'))

    def drop_tables(self):
        self.drop_schema()
        db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'drop_tables.sql'))

    def drop_schema(self):
        db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'drop_schema.sql'))

    def drop_types(self):
        db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'drop_types.sql'))

    def assertRedirects(self, response, location, message=None, permanent=False):
        """Override Flask testing's assertRedirects, which doesn't know about the new
        redirect behaviour from RFC 9110 (https://github.com/pallets/werkzeug/pull/2354)"""
        if permanent:
            valid_status_codes = (301, 308)
        else:
            valid_status_codes = (301, 302, 303, 305, 307, 308)

        valid_status_code_str = ', '.join(str(code) for code in valid_status_codes)
        not_redirect = "HTTP Status %s expected but got %d" % (valid_status_code_str, response.status_code)

        self.assertIn(response.status_code, valid_status_codes, message or not_redirect)
        location_mismatch = "Expected redirect location %s but got %s" % (response.location, location)
        self.assertTrue(response.location.endswith(location), message or location_mismatch)

    assert_redirects = assertRedirects

    def data_filename(self, mbid):
        """ Get the expected filename of a test datafile given its mbid """
        return os.path.join(DB_TEST_DATA_PATH, mbid + '.json')

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
