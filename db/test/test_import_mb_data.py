from db.testing import DatabaseTestCase, TEST_DATA_PATH, gid_types
from brainzutils import musicbrainz_db
import db
import db.exceptions
import db.import_mb_data
import os.path
import mock
import uuid
import datetime
import psycopg2


class DataMusicBrainzDBTestCase(DatabaseTestCase):

    def setUp(self):
        super(DataMusicBrainzDBTestCase, self).setUp()


    def test_load_and_write_area(self):

        # area_type
        data = [(1, u'Country', None, 1, u'Country is used for areas included (or previously included) in ISO 3166-1, e.g. United States.', uuid.UUID('06dd0ae4-8c74-30bb-b43d-95dcedf961de')),
            (3, u'City', None, 3, u'City is used for settlements of any size, including towns and villages.', uuid.UUID('6fd8f29a-3d0a-32fc-980d-ea697b69da78'))
        ]

        with db.engine.begin() as connection:
            db.import_mb_data.write_area_type(connection, data)
            self.assertEqual(data, db.import_mb_data.load_musicbrainz_schema_data(connection, 'area_type'))

        # area
        data = [(24482, uuid.UUID('915a5576-b30c-4160-93cd-e1185cebb6ac'), u'Smithville', 3, 0,
            datetime.datetime(2013, 11, 14, 1, 33, 0, 377353, tzinfo=psycopg2.tz.FixedOffsetTimezone(offset=0, name=None)), None, None, None, None, None, None, False, u''),
            (222, uuid.UUID('489ce91b-6658-3307-9877-795b68554c98'), u'United States', 1, 0,
            datetime.datetime(2013, 6, 15, 18, 6, 39, 593230, tzinfo=psycopg2.tz.FixedOffsetTimezone(offset=0, name=None)), None, None, None, None, None, None, False, u''),
            (5099, uuid.UUID('29a709d8-0320-493e-8d0c-f2c386662b7f'), u'Chicago', 3, 0,
            datetime.datetime(2013, 5, 24, 20, 27, 13, 405462, tzinfo=psycopg2.tz.FixedOffsetTimezone(offset=0, name=None)), None, None, None, None, None, None, False, u'')
        ]

        with db.engine.begin() as connection:
            db.import_mb_data.write_area(connection, data)
            self.assertEqual(data, db.import_mb_data.load_musicbrainz_schema_data(connection, 'area'))


    def test_load_and_write_artist(self):

        # area_type
        data = [(1, u'Country', None, 1, u'Country is used for areas included (or previously included) in ISO 3166-1, e.g. United States.', uuid.UUID('06dd0ae4-8c74-30bb-b43d-95dcedf961de')),
            (3, u'City', None, 3, u'City is used for settlements of any size, including towns and villages.', uuid.UUID('6fd8f29a-3d0a-32fc-980d-ea697b69da78'))
        ]

        with db.engine.begin() as connection:
            db.import_mb_data.write_area_type(connection, data)
            self.assertEqual(data, db.import_mb_data.load_musicbrainz_schema_data(connection, 'area_type'))

        # area
        data = [(24482, uuid.UUID('915a5576-b30c-4160-93cd-e1185cebb6ac'), u'Smithville', 3, 0,
            datetime.datetime(2013, 11, 14, 1, 33, 0, 377353, tzinfo=psycopg2.tz.FixedOffsetTimezone(offset=0, name=None)), None, None, None, None, None, None, False, u''),
            (222, uuid.UUID('489ce91b-6658-3307-9877-795b68554c98'), u'United States', 1, 0,
            datetime.datetime(2013, 6, 15, 18, 6, 39, 593230, tzinfo=psycopg2.tz.FixedOffsetTimezone(offset=0, name=None)), None, None, None, None, None, None, False, u''),
            (5099, uuid.UUID('29a709d8-0320-493e-8d0c-f2c386662b7f'), u'Chicago', 3, 0,
            datetime.datetime(2013, 5, 24, 20, 27, 13, 405462, tzinfo=psycopg2.tz.FixedOffsetTimezone(offset=0, name=None)), None, None, None, None, None, None, False, u'')
        ]

        with db.engine.begin() as connection:
            db.import_mb_data.write_area(connection, data)
            self.assertEqual(data, db.import_mb_data.load_musicbrainz_schema_data(connection, 'area'))

        # artist_type
        data = [(1, u'Person', None, 1, None, uuid.UUID('b6e035f4-3ce9-331c-97df-83397230b0df')),
            (2, u'Group', None, 2, None, uuid.UUID('e431f5f6-b5d2-343d-8b36-72607fffb74b'))
        ]

        with db.engine.begin() as connection:
            db.import_mb_data.write_artist_type(connection, data)
            self.assertEqual(data, db.import_mb_data.load_musicbrainz_schema_data(connection, 'artist_type'))

        # gender
        data = [(1, u'Male', None, 1, None, uuid.UUID('36d3d30a-839d-3eda-8cb3-29be4384e4a9')),
            (2, u'Female', None, 2, None, uuid.UUID('93452b5a-a947-30c8-934f-6a4056b151c2'))
        ]

        with db.engine.begin() as connection:
            db.import_mb_data.write_gender(connection, data)
            self.assertEqual(data, db.import_mb_data.load_musicbrainz_schema_data(connection, 'gender'))

        # artist
        data = [(6747, uuid.UUID('1b62df85-00d2-464f-81bc-a5c0cdcad278'), u'Tampa Red', u'Tampa Red', 1904, 1, 8, 1981, 3, 19, 1, 222, 1, u'', 0,
            datetime.datetime(2016, 8, 21, 5, 0, 58, 662928, tzinfo=psycopg2.tz.FixedOffsetTimezone(offset=0, name=None)), True, 24482, 5099)
        ]

        with db.engine.begin() as connection:
            db.import_mb_data.write_artist(connection, data)
            self.assertEqual(data, db.import_mb_data.load_musicbrainz_schema_data(connection, 'artist'))


    def test_load_and_write_artist_gid_redirect(self):
        # area_type
        data = [(1, u'Country', None, 1, u'Country is used for areas included (or previously included) in ISO 3166-1, e.g. United States.', uuid.UUID('06dd0ae4-8c74-30bb-b43d-95dcedf961de')),
            (3, u'City', None, 3, u'City is used for settlements of any size, including towns and villages.', uuid.UUID('6fd8f29a-3d0a-32fc-980d-ea697b69da78'))
        ]

        with db.engine.begin() as connection:
            db.import_mb_data.write_area_type(connection, data)
            self.assertEqual(data, db.import_mb_data.load_musicbrainz_schema_data(connection, 'area_type'))

        # area
        data = [(24482, uuid.UUID('915a5576-b30c-4160-93cd-e1185cebb6ac'), u'Smithville', 3, 0,
            datetime.datetime(2013, 11, 14, 1, 33, 0, 377353, tzinfo=psycopg2.tz.FixedOffsetTimezone(offset=0, name=None)), None, None, None, None, None, None, False, u''),
            (222, uuid.UUID('489ce91b-6658-3307-9877-795b68554c98'), u'United States', 1, 0,
            datetime.datetime(2013, 6, 15, 18, 6, 39, 593230, tzinfo=psycopg2.tz.FixedOffsetTimezone(offset=0, name=None)), None, None, None, None, None, None, False, u''),
            (5099, uuid.UUID('29a709d8-0320-493e-8d0c-f2c386662b7f'), u'Chicago', 3, 0,
            datetime.datetime(2013, 5, 24, 20, 27, 13, 405462, tzinfo=psycopg2.tz.FixedOffsetTimezone(offset=0, name=None)), None, None, None, None, None, None, False, u'')
        ]

        with db.engine.begin() as connection:
            db.import_mb_data.write_area(connection, data)
            self.assertEqual(data, db.import_mb_data.load_musicbrainz_schema_data(connection, 'area'))

        # artist_type
        data = [(1, u'Person', None, 1, None, uuid.UUID('b6e035f4-3ce9-331c-97df-83397230b0df')),
            (2, u'Group', None, 2, None, uuid.UUID('e431f5f6-b5d2-343d-8b36-72607fffb74b'))
        ]

        with db.engine.begin() as connection:
            db.import_mb_data.write_artist_type(connection, data)
            self.assertEqual(data, db.import_mb_data.load_musicbrainz_schema_data(connection, 'artist_type'))

        # gender
        data = [(1, u'Male', None, 1, None, uuid.UUID('36d3d30a-839d-3eda-8cb3-29be4384e4a9')),
            (2, u'Female', None, 2, None, uuid.UUID('93452b5a-a947-30c8-934f-6a4056b151c2'))
        ]

        with db.engine.begin() as connection:
            db.import_mb_data.write_gender(connection, data)
            self.assertEqual(data, db.import_mb_data.load_musicbrainz_schema_data(connection, 'gender'))

        # artist
        data = [(6747, uuid.UUID('1b62df85-00d2-464f-81bc-a5c0cdcad278'), u'Tampa Red', u'Tampa Red', 1904, 1, 8, 1981, 3, 19, 1, 222, 1, u'', 0,
            datetime.datetime(2016, 8, 21, 5, 0, 58, 662928, tzinfo=psycopg2.tz.FixedOffsetTimezone(offset=0, name=None)), True, 24482, 5099)
        ]

        with db.engine.begin() as connection:
            db.import_mb_data.write_artist(connection, data)
            self.assertEqual(data, db.import_mb_data.load_musicbrainz_schema_data(connection, 'artist'))

        # artist_gid_redirect
        data = [(uuid.UUID('6873559d-8cb9-494d-9f78-4c1eeab1f851'), 6747, datetime.datetime(2016, 3, 13, 23, 0, 21, 981437, tzinfo=psycopg2.tz.FixedOffsetTimezone(offset=0, name=None)))]

        with db.engine.begin() as connection:
            db.import_mb_data.write_artist_gid_redirect(connection, data)
            self.assertEqual(data, db.import_mb_data.load_musicbrainz_schema_data(connection, 'artist_gid_redirect'))


    def test_load_and_write_artist_credit(self):
        # artist_credit
        data = [(1418, u'Tangerine Dream', 1, 13729, datetime.datetime(2011, 5, 16, 16, 32, 11, 963929, tzinfo=psycopg2.tz.FixedOffsetTimezone(offset=0, name=None))),
            (399541, u'Taylor Swift', 1, 3139, datetime.datetime(2011, 5, 16, 16, 32, 11, 963929, tzinfo=psycopg2.tz.FixedOffsetTimezone(offset=0, name=None))),
            (73502, u'Georg Friedrich Handel', 1, 27041, datetime.datetime(2011, 5, 16, 16, 32, 11, 963929, tzinfo=psycopg2.tz.FixedOffsetTimezone(offset=0, name=None))),
            (831440, u'George Frideric Handel', 1, 24955, datetime.datetime(2011, 6, 19, 7, 36, 56, 8576, tzinfo=psycopg2.tz.FixedOffsetTimezone(offset=0, name=None))),
            (847994, u'Handel', 1, 717, datetime.datetime(2011, 8, 11, 19, 43, 1, 279447, tzinfo=psycopg2.tz.FixedOffsetTimezone(offset=0, name=None))),
            (6747, u'Tampa Red', 1, 1600, datetime.datetime(2011, 5, 16, 16, 32, 11, 963929, tzinfo=psycopg2.tz.FixedOffsetTimezone(offset=0, name=None)))
        ]

        with db.engine.begin() as connection:
            db.import_mb_data.write_artist_credit(connection, data)
            self.assertEqual(data, db.import_mb_data.load_musicbrainz_schema_data(connection, 'artist_credit'))


    def test_load_and_write_artist_credit_name(self):

        # artist_credit
        data = [(1418, u'Tangerine Dream', 1, 13729, datetime.datetime(2011, 5, 16, 16, 32, 11, 963929, tzinfo=psycopg2.tz.FixedOffsetTimezone(offset=0, name=None))),
            (399541, u'Taylor Swift', 1, 3139, datetime.datetime(2011, 5, 16, 16, 32, 11, 963929, tzinfo=psycopg2.tz.FixedOffsetTimezone(offset=0, name=None))),
            (73502, u'Georg Friedrich Handel', 1, 27041, datetime.datetime(2011, 5, 16, 16, 32, 11, 963929, tzinfo=psycopg2.tz.FixedOffsetTimezone(offset=0, name=None))),
            (831440, u'George Frideric Handel', 1, 24955, datetime.datetime(2011, 6, 19, 7, 36, 56, 8576, tzinfo=psycopg2.tz.FixedOffsetTimezone(offset=0, name=None))),
            (847994, u'Handel', 1, 717, datetime.datetime(2011, 8, 11, 19, 43, 1, 279447, tzinfo=psycopg2.tz.FixedOffsetTimezone(offset=0, name=None))),
            (6747, u'Tampa Red', 1, 1600, datetime.datetime(2011, 5, 16, 16, 32, 11, 963929, tzinfo=psycopg2.tz.FixedOffsetTimezone(offset=0, name=None)))
        ]

        with db.engine.begin() as connection:
            db.import_mb_data.write_artist_credit(connection, data)
            self.assertEqual(data, db.import_mb_data.load_musicbrainz_schema_data(connection, 'artist_credit'))

        # area_type
        data = [(1, u'Country', None, 1, u'Country is used for areas included (or previously included) in ISO 3166-1, e.g. United States.', uuid.UUID('06dd0ae4-8c74-30bb-b43d-95dcedf961de')),
            (3, u'City', None, 3, u'City is used for settlements of any size, including towns and villages.', uuid.UUID('6fd8f29a-3d0a-32fc-980d-ea697b69da78'))
        ]

        with db.engine.begin() as connection:
            db.import_mb_data.write_area_type(connection, data)
            self.assertEqual(data, db.import_mb_data.load_musicbrainz_schema_data(connection, 'area_type'))

        # area
        data = [(24482, uuid.UUID('915a5576-b30c-4160-93cd-e1185cebb6ac'), u'Smithville', 3, 0,
            datetime.datetime(2013, 11, 14, 1, 33, 0, 377353, tzinfo=psycopg2.tz.FixedOffsetTimezone(offset=0, name=None)), None, None, None, None, None, None, False, u''),
            (222, uuid.UUID('489ce91b-6658-3307-9877-795b68554c98'), u'United States', 1, 0,
            datetime.datetime(2013, 6, 15, 18, 6, 39, 593230, tzinfo=psycopg2.tz.FixedOffsetTimezone(offset=0, name=None)), None, None, None, None, None, None, False, u''),
            (5099, uuid.UUID('29a709d8-0320-493e-8d0c-f2c386662b7f'), u'Chicago', 3, 0,
            datetime.datetime(2013, 5, 24, 20, 27, 13, 405462, tzinfo=psycopg2.tz.FixedOffsetTimezone(offset=0, name=None)), None, None, None, None, None, None, False, u'')
        ]

        with db.engine.begin() as connection:
            db.import_mb_data.write_area(connection, data)
            self.assertEqual(data, db.import_mb_data.load_musicbrainz_schema_data(connection, 'area'))

        # artist_type
        data = [(1, u'Person', None, 1, None, uuid.UUID('b6e035f4-3ce9-331c-97df-83397230b0df')),
            (2, u'Group', None, 2, None, uuid.UUID('e431f5f6-b5d2-343d-8b36-72607fffb74b'))
        ]

        with db.engine.begin() as connection:
            db.import_mb_data.write_artist_type(connection, data)
            self.assertEqual(data, db.import_mb_data.load_musicbrainz_schema_data(connection, 'artist_type'))

        # gender
        data = [(1, u'Male', None, 1, None, uuid.UUID('36d3d30a-839d-3eda-8cb3-29be4384e4a9')),
            (2, u'Female', None, 2, None, uuid.UUID('93452b5a-a947-30c8-934f-6a4056b151c2'))
        ]

        with db.engine.begin() as connection:
            db.import_mb_data.write_gender(connection, data)
            self.assertEqual(data, db.import_mb_data.load_musicbrainz_schema_data(connection, 'gender'))

        # artist
        data = [(6747, uuid.UUID('1b62df85-00d2-464f-81bc-a5c0cdcad278'), u'Tampa Red', u'Tampa Red', 1904, 1, 8, 1981, 3, 19, 1, 222, 1, u'', 0,
            datetime.datetime(2016, 8, 21, 5, 0, 58, 662928, tzinfo=psycopg2.tz.FixedOffsetTimezone(offset=0, name=None)), True, 24482, 5099)
        ]

        with db.engine.begin() as connection:
            db.import_mb_data.write_artist(connection, data)
            self.assertEqual(data, db.import_mb_data.load_musicbrainz_schema_data(connection, 'artist'))

        # artist_credit_name
        data = [(6747, 0, 6747, u'Tampa Red', u'')]

        with db.engine.begin() as connection:
            db.import_mb_data.write_artist_credit_name(connection, data)
            self.assertEqual(data, db.import_mb_data.load_musicbrainz_schema_data(connection, 'artist_credit_name'))


    def test_load_and_write_recording(self):
        # artist_credit
        data = [(1418, u'Tangerine Dream', 1, 13729, datetime.datetime(2011, 5, 16, 16, 32, 11, 963929, tzinfo=psycopg2.tz.FixedOffsetTimezone(offset=0, name=None))),
            (399541, u'Taylor Swift', 1, 3139, datetime.datetime(2011, 5, 16, 16, 32, 11, 963929, tzinfo=psycopg2.tz.FixedOffsetTimezone(offset=0, name=None))),
            (73502, u'Georg Friedrich Handel', 1, 27041, datetime.datetime(2011, 5, 16, 16, 32, 11, 963929, tzinfo=psycopg2.tz.FixedOffsetTimezone(offset=0, name=None))),
            (831440, u'George Frideric Handel', 1, 24955, datetime.datetime(2011, 6, 19, 7, 36, 56, 8576, tzinfo=psycopg2.tz.FixedOffsetTimezone(offset=0, name=None))),
            (847994, u'Handel', 1, 717, datetime.datetime(2011, 8, 11, 19, 43, 1, 279447, tzinfo=psycopg2.tz.FixedOffsetTimezone(offset=0, name=None))),
            (6747, u'Tampa Red', 1, 1600, datetime.datetime(2011, 5, 16, 16, 32, 11, 963929, tzinfo=psycopg2.tz.FixedOffsetTimezone(offset=0, name=None)))
        ]

        with db.engine.begin() as connection:
            db.import_mb_data.write_artist_credit(connection, data)
            self.assertEqual(data, db.import_mb_data.load_musicbrainz_schema_data(connection, 'artist_credit'))

        # recording
        data = [(11768371, uuid.UUID('d51cf7fb-97e1-4070-a40b-b03707f91c92'), u'(Rinaldo, HWV 7: Act I. "Combatti da forte" (Almirena)', 73502, 203000, u'', 0, None, False),
            (8598260, uuid.UUID('9086b742-358b-4f73-9a14-84cb1a9ce4ce'), u'Love Story', 399541, 235000, u'', 0, None, False)
        ]

        with db.engine.begin() as connection:
            db.import_mb_data.write_recording(connection, data)
            self.assertEqual(data, db.import_mb_data.load_musicbrainz_schema_data(connection, 'recording'))


    def test_load_and_write_recording_gid_redirect(self):
        # artist_credit
        data = [(1418, u'Tangerine Dream', 1, 13729, datetime.datetime(2011, 5, 16, 16, 32, 11, 963929, tzinfo=psycopg2.tz.FixedOffsetTimezone(offset=0, name=None))),
            (399541, u'Taylor Swift', 1, 3139, datetime.datetime(2011, 5, 16, 16, 32, 11, 963929, tzinfo=psycopg2.tz.FixedOffsetTimezone(offset=0, name=None))),
            (73502, u'Georg Friedrich Handel', 1, 27041, datetime.datetime(2011, 5, 16, 16, 32, 11, 963929, tzinfo=psycopg2.tz.FixedOffsetTimezone(offset=0, name=None))),
            (831440, u'George Frideric Handel', 1, 24955, datetime.datetime(2011, 6, 19, 7, 36, 56, 8576, tzinfo=psycopg2.tz.FixedOffsetTimezone(offset=0, name=None))),
            (847994, u'Handel', 1, 717, datetime.datetime(2011, 8, 11, 19, 43, 1, 279447, tzinfo=psycopg2.tz.FixedOffsetTimezone(offset=0, name=None))),
            (6747, u'Tampa Red', 1, 1600, datetime.datetime(2011, 5, 16, 16, 32, 11, 963929, tzinfo=psycopg2.tz.FixedOffsetTimezone(offset=0, name=None)))
        ]

        with db.engine.begin() as connection:
            db.import_mb_data.write_artist_credit(connection, data)
            self.assertEqual(data, db.import_mb_data.load_musicbrainz_schema_data(connection, 'artist_credit'))

        # recording
        data = [(11768371, uuid.UUID('d51cf7fb-97e1-4070-a40b-b03707f91c92'), u'(Rinaldo, HWV 7: Act I. "Combatti da forte" (Almirena)', 73502, 203000, u'', 0, None, False),
            (8598260, uuid.UUID('9086b742-358b-4f73-9a14-84cb1a9ce4ce'), u'Love Story', 399541, 235000, u'', 0, None, False)
        ]

        with db.engine.begin() as connection:
            db.import_mb_data.write_recording(connection, data)
            self.assertEqual(data, db.import_mb_data.load_musicbrainz_schema_data(connection, 'recording'))

        # recording_gid_redirect
        data = [(uuid.UUID('05e1ab2e-f54f-464b-a1fd-fcc6bceaaa20'), 8598260, datetime.datetime(2011, 5, 16, 16, 8, 20, 288158, tzinfo=psycopg2.tz.FixedOffsetTimezone(offset=0, name=None)))]

        with db.engine.begin() as connection:
            db.import_mb_data.write_recording_gid_redirect(connection, data)
            self.assertEqual(data, db.import_mb_data.load_musicbrainz_schema_data(connection, 'recording_gid_redirect'))


    def test_load_and_write_release_group(self):
        # artist_credit
        data = [(1418, u'Tangerine Dream', 1, 13729, datetime.datetime(2011, 5, 16, 16, 32, 11, 963929, tzinfo=psycopg2.tz.FixedOffsetTimezone(offset=0, name=None))),
            (399541, u'Taylor Swift', 1, 3139, datetime.datetime(2011, 5, 16, 16, 32, 11, 963929, tzinfo=psycopg2.tz.FixedOffsetTimezone(offset=0, name=None))),
            (73502, u'Georg Friedrich Handel', 1, 27041, datetime.datetime(2011, 5, 16, 16, 32, 11, 963929, tzinfo=psycopg2.tz.FixedOffsetTimezone(offset=0, name=None))),
            (831440, u'George Frideric Handel', 1, 24955, datetime.datetime(2011, 6, 19, 7, 36, 56, 8576, tzinfo=psycopg2.tz.FixedOffsetTimezone(offset=0, name=None))),
            (847994, u'Handel', 1, 717, datetime.datetime(2011, 8, 11, 19, 43, 1, 279447, tzinfo=psycopg2.tz.FixedOffsetTimezone(offset=0, name=None))),
            (6747, u'Tampa Red', 1, 1600, datetime.datetime(2011, 5, 16, 16, 32, 11, 963929, tzinfo=psycopg2.tz.FixedOffsetTimezone(offset=0, name=None)))
        ]

        with db.engine.begin() as connection:
            db.import_mb_data.write_artist_credit(connection, data)
            self.assertEqual(data, db.import_mb_data.load_musicbrainz_schema_data(connection, 'artist_credit'))

        # release_group_primary_type
        data = [(1, u'Album', None, 1, None, uuid.UUID('f529b476-6e62-324f-b0aa-1f3e33d313fc'))]

        with db.engine.begin() as connection:
            db.import_mb_data.write_release_group_primary_type(connection, data)
            self.assertEqual(data, db.import_mb_data.load_musicbrainz_schema_data(connection, 'release_group_primary_type'))

        # release_group
        data = [(631361, uuid.UUID('2ec35fc4-6797-3324-b775-9a3df3d4723a'), u'The Masterworks', 73502, 1, u'', 0,
            datetime.datetime(2012, 5, 15, 19, 1, 58, 718541, tzinfo=psycopg2.tz.FixedOffsetTimezone(offset=0, name=None))),
            (617137, uuid.UUID('c834f5ee-d362-3da7-966b-8915a86e808c'), u'1981-08-29: Tangerine Tree Volume 53: Berlin 1981', 1418, 1, u'', 0,
            datetime.datetime(2016, 9, 21, 23, 0, 26, 94608, tzinfo=psycopg2.tz.FixedOffsetTimezone(offset=0, name=None)))
        ]

        with db.engine.begin() as connection:
            db.import_mb_data.write_release_group(connection, data)
            self.assertEqual(data, db.import_mb_data.load_musicbrainz_schema_data(connection, 'release_group'))


    def test_load_and_write_release_group_gid_redirect(self):
        # artist_credit
        data = [(1418, u'Tangerine Dream', 1, 13729, datetime.datetime(2011, 5, 16, 16, 32, 11, 963929, tzinfo=psycopg2.tz.FixedOffsetTimezone(offset=0, name=None))),
            (399541, u'Taylor Swift', 1, 3139, datetime.datetime(2011, 5, 16, 16, 32, 11, 963929, tzinfo=psycopg2.tz.FixedOffsetTimezone(offset=0, name=None))),
            (73502, u'Georg Friedrich Handel', 1, 27041, datetime.datetime(2011, 5, 16, 16, 32, 11, 963929, tzinfo=psycopg2.tz.FixedOffsetTimezone(offset=0, name=None))),
            (831440, u'George Frideric Handel', 1, 24955, datetime.datetime(2011, 6, 19, 7, 36, 56, 8576, tzinfo=psycopg2.tz.FixedOffsetTimezone(offset=0, name=None))),
            (847994, u'Handel', 1, 717, datetime.datetime(2011, 8, 11, 19, 43, 1, 279447, tzinfo=psycopg2.tz.FixedOffsetTimezone(offset=0, name=None))),
            (6747, u'Tampa Red', 1, 1600, datetime.datetime(2011, 5, 16, 16, 32, 11, 963929, tzinfo=psycopg2.tz.FixedOffsetTimezone(offset=0, name=None)))
        ]

        with db.engine.begin() as connection:
            db.import_mb_data.write_artist_credit(connection, data)
            self.assertEqual(data, db.import_mb_data.load_musicbrainz_schema_data(connection, 'artist_credit'))

        # release_group_primary_type
        data = [(1, u'Album', None, 1, None, uuid.UUID('f529b476-6e62-324f-b0aa-1f3e33d313fc'))]

        with db.engine.begin() as connection:
            db.import_mb_data.write_release_group_primary_type(connection, data)
            self.assertEqual(data, db.import_mb_data.load_musicbrainz_schema_data(connection, 'release_group_primary_type'))

        # release_group
        data = [(631361, uuid.UUID('2ec35fc4-6797-3324-b775-9a3df3d4723a'), u'The Masterworks', 73502, 1, u'', 0,
            datetime.datetime(2012, 5, 15, 19, 1, 58, 718541, tzinfo=psycopg2.tz.FixedOffsetTimezone(offset=0, name=None))),
            (617137, uuid.UUID('c834f5ee-d362-3da7-966b-8915a86e808c'), u'1981-08-29: Tangerine Tree Volume 53: Berlin 1981', 1418, 1, u'', 0,
            datetime.datetime(2016, 9, 21, 23, 0, 26, 94608, tzinfo=psycopg2.tz.FixedOffsetTimezone(offset=0, name=None)))
        ]

        with db.engine.begin() as connection:
            db.import_mb_data.write_release_group(connection, data)
            self.assertEqual(data, db.import_mb_data.load_musicbrainz_schema_data(connection, 'release_group'))

        # release_group_gid_redirect
        data = [(uuid.UUID('21f0a3e8-c37b-33a1-b769-daf16e4e252e'), 617137, datetime.datetime(2011, 5, 16, 14, 57, 6, 530063, tzinfo=psycopg2.tz.FixedOffsetTimezone(offset=0, name=None)))]

        with db.engine.begin() as connection:
            db.import_mb_data.write_release_group_gid_redirect(connection, data)
            self.assertEqual(data, db.import_mb_data.load_musicbrainz_schema_data(connection, 'release_group_gid_redirect'))


    def test_load_and_write_release(self):
        # artist_credit
        data = [(1418, u'Tangerine Dream', 1, 13729, datetime.datetime(2011, 5, 16, 16, 32, 11, 963929, tzinfo=psycopg2.tz.FixedOffsetTimezone(offset=0, name=None))),
            (399541, u'Taylor Swift', 1, 3139, datetime.datetime(2011, 5, 16, 16, 32, 11, 963929, tzinfo=psycopg2.tz.FixedOffsetTimezone(offset=0, name=None))),
            (73502, u'Georg Friedrich Handel', 1, 27041, datetime.datetime(2011, 5, 16, 16, 32, 11, 963929, tzinfo=psycopg2.tz.FixedOffsetTimezone(offset=0, name=None))),
            (831440, u'George Frideric Handel', 1, 24955, datetime.datetime(2011, 6, 19, 7, 36, 56, 8576, tzinfo=psycopg2.tz.FixedOffsetTimezone(offset=0, name=None))),
            (847994, u'Handel', 1, 717, datetime.datetime(2011, 8, 11, 19, 43, 1, 279447, tzinfo=psycopg2.tz.FixedOffsetTimezone(offset=0, name=None))),
            (6747, u'Tampa Red', 1, 1600, datetime.datetime(2011, 5, 16, 16, 32, 11, 963929, tzinfo=psycopg2.tz.FixedOffsetTimezone(offset=0, name=None)))
        ]

        with db.engine.begin() as connection:
            db.import_mb_data.write_artist_credit(connection, data)
            self.assertEqual(data, db.import_mb_data.load_musicbrainz_schema_data(connection, 'artist_credit'))

        # release_group_primary_type
        data = [(1, u'Album', None, 1, None, uuid.UUID('f529b476-6e62-324f-b0aa-1f3e33d313fc'))]

        with db.engine.begin() as connection:
            db.import_mb_data.write_release_group_primary_type(connection, data)
            self.assertEqual(data, db.import_mb_data.load_musicbrainz_schema_data(connection, 'release_group_primary_type'))

        # release_group
        data = [(631361, uuid.UUID('2ec35fc4-6797-3324-b775-9a3df3d4723a'), u'The Masterworks', 73502, 1, u'', 0,
            datetime.datetime(2012, 5, 15, 19, 1, 58, 718541, tzinfo=psycopg2.tz.FixedOffsetTimezone(offset=0, name=None))),
            (617137, uuid.UUID('c834f5ee-d362-3da7-966b-8915a86e808c'), u'1981-08-29: Tangerine Tree Volume 53: Berlin 1981', 1418, 1, u'', 0,
            datetime.datetime(2016, 9, 21, 23, 0, 26, 94608, tzinfo=psycopg2.tz.FixedOffsetTimezone(offset=0, name=None)))
        ]

        with db.engine.begin() as connection:
            db.import_mb_data.write_release_group(connection, data)
            self.assertEqual(data, db.import_mb_data.load_musicbrainz_schema_data(connection, 'release_group'))

        # language
        data = [(120, u'eng', u'eng', u'en', u'English', 2, None)]

        with db.engine.begin() as connection:
            db.import_mb_data.write_language(connection, data)
            self.assertEqual(data, db.import_mb_data.load_musicbrainz_schema_data(connection, 'language'))

        # release_status
        data = [(1, u'Official', None, 1, u'Any release officially sanctioned by the artist and/or their record company. Most releases will fit into this category.',
            uuid.UUID('4e304316-386d-3409-af2e-78857eec5cfe'))]

        with db.engine.begin() as connection:
            db.import_mb_data.write_release_status(connection, data)
            self.assertEqual(data, db.import_mb_data.load_musicbrainz_schema_data(connection, 'release_status'))

        # release_packaging
        data = [(1, u'Jewel Case', None, 0, u'The traditional CD case, made of hard, brittle plastic.',
            uuid.UUID('ec27701a-4a22-37f4-bfac-6616e0f9750a'))
        ]

        with db.engine.begin() as connection:
            db.import_mb_data.write_release_packaging(connection, data)
            self.assertEqual(data, db.import_mb_data.load_musicbrainz_schema_data(connection, 'release_packaging'))

        # script
        data = [(28, u'Latn', u'215', u'Latin', 4)]

        with db.engine.begin() as connection:
            db.import_mb_data.write_script(connection, data)
            self.assertEqual(data, db.import_mb_data.load_musicbrainz_schema_data(connection, 'script'))

        # release
        data = [(692283, uuid.UUID('a830f892-6be0-35f0-a392-b91d89d89a94'), u'The Masterworks', 847994, 631361, 1, None, 120, 28, u'5028421923901', u'', 0, -1,
            datetime.datetime(2018, 5, 13, 11, 0, 22, 832493, tzinfo=psycopg2.tz.FixedOffsetTimezone(offset=0, name=None)))
        ]

        with db.engine.begin() as connection:
            db.import_mb_data.write_release(connection, data)
            self.assertEqual(data, db.import_mb_data.load_musicbrainz_schema_data(connection, 'release'))


    def test_load_and_write_release_gid_redirect(self):
        # artist_credit
        data = [(1418, u'Tangerine Dream', 1, 13729, datetime.datetime(2011, 5, 16, 16, 32, 11, 963929, tzinfo=psycopg2.tz.FixedOffsetTimezone(offset=0, name=None))),
            (399541, u'Taylor Swift', 1, 3139, datetime.datetime(2011, 5, 16, 16, 32, 11, 963929, tzinfo=psycopg2.tz.FixedOffsetTimezone(offset=0, name=None))),
            (73502, u'Georg Friedrich Handel', 1, 27041, datetime.datetime(2011, 5, 16, 16, 32, 11, 963929, tzinfo=psycopg2.tz.FixedOffsetTimezone(offset=0, name=None))),
            (831440, u'George Frideric Handel', 1, 24955, datetime.datetime(2011, 6, 19, 7, 36, 56, 8576, tzinfo=psycopg2.tz.FixedOffsetTimezone(offset=0, name=None))),
            (847994, u'Handel', 1, 717, datetime.datetime(2011, 8, 11, 19, 43, 1, 279447, tzinfo=psycopg2.tz.FixedOffsetTimezone(offset=0, name=None))),
            (6747, u'Tampa Red', 1, 1600, datetime.datetime(2011, 5, 16, 16, 32, 11, 963929, tzinfo=psycopg2.tz.FixedOffsetTimezone(offset=0, name=None)))
        ]

        with db.engine.begin() as connection:
            db.import_mb_data.write_artist_credit(connection, data)
            self.assertEqual(data, db.import_mb_data.load_musicbrainz_schema_data(connection, 'artist_credit'))

        # release_group_primary_type
        data = [(1, u'Album', None, 1, None, uuid.UUID('f529b476-6e62-324f-b0aa-1f3e33d313fc'))]

        with db.engine.begin() as connection:
            db.import_mb_data.write_release_group_primary_type(connection, data)
            self.assertEqual(data, db.import_mb_data.load_musicbrainz_schema_data(connection, 'release_group_primary_type'))

        # release_group
        data = [(631361, uuid.UUID('2ec35fc4-6797-3324-b775-9a3df3d4723a'), u'The Masterworks', 73502, 1, u'', 0,
            datetime.datetime(2012, 5, 15, 19, 1, 58, 718541, tzinfo=psycopg2.tz.FixedOffsetTimezone(offset=0, name=None))),
            (617137, uuid.UUID('c834f5ee-d362-3da7-966b-8915a86e808c'), u'1981-08-29: Tangerine Tree Volume 53: Berlin 1981', 1418, 1, u'', 0,
            datetime.datetime(2016, 9, 21, 23, 0, 26, 94608, tzinfo=psycopg2.tz.FixedOffsetTimezone(offset=0, name=None)))
        ]

        with db.engine.begin() as connection:
            db.import_mb_data.write_release_group(connection, data)
            self.assertEqual(data, db.import_mb_data.load_musicbrainz_schema_data(connection, 'release_group'))

        # language
        data = [(120, u'eng', u'eng', u'en', u'English', 2, None)]

        with db.engine.begin() as connection:
            db.import_mb_data.write_language(connection, data)
            self.assertEqual(data, db.import_mb_data.load_musicbrainz_schema_data(connection, 'language'))

        # release_status
        data = [(1, u'Official', None, 1, u'Any release officially sanctioned by the artist and/or their record company. Most releases will fit into this category.',
            uuid.UUID('4e304316-386d-3409-af2e-78857eec5cfe'))]

        with db.engine.begin() as connection:
            db.import_mb_data.write_release_status(connection, data)
            self.assertEqual(data, db.import_mb_data.load_musicbrainz_schema_data(connection, 'release_status'))

        # release_packaging
        data = [(1, u'Jewel Case', None, 0, u'The traditional CD case, made of hard, brittle plastic.',
            uuid.UUID('ec27701a-4a22-37f4-bfac-6616e0f9750a'))
        ]

        with db.engine.begin() as connection:
            db.import_mb_data.write_release_packaging(connection, data)
            self.assertEqual(data, db.import_mb_data.load_musicbrainz_schema_data(connection, 'release_packaging'))

        # script
        data = [(28, u'Latn', u'215', u'Latin', 4)]

        with db.engine.begin() as connection:
            db.import_mb_data.write_script(connection, data)
            self.assertEqual(data, db.import_mb_data.load_musicbrainz_schema_data(connection, 'script'))

        # release
        data = [(692283, uuid.UUID('a830f892-6be0-35f0-a392-b91d89d89a94'), u'The Masterworks', 847994, 631361, 1, None, 120, 28, u'5028421923901', u'', 0, -1,
            datetime.datetime(2018, 5, 13, 11, 0, 22, 832493, tzinfo=psycopg2.tz.FixedOffsetTimezone(offset=0, name=None)))
        ]

        with db.engine.begin() as connection:
            db.import_mb_data.write_release(connection, data)
            self.assertEqual(data, db.import_mb_data.load_musicbrainz_schema_data(connection, 'release'))


    def test_load_and_write_medium(self):
        # medium_format
        data = [(1, u'CD', None, 0, 1982, True, None, uuid.UUID('9712d52a-4509-3d4b-a1a2-67c88c643e31'))]

        with db.engine.begin() as connection:
            db.import_mb_data.write_medium_format(connection, data)
            self.assertEqual(data, db.import_mb_data.load_musicbrainz_schema_data(connection, 'medium_format'))

        # artist_credit
        data = [(1418, u'Tangerine Dream', 1, 13729, datetime.datetime(2011, 5, 16, 16, 32, 11, 963929, tzinfo=psycopg2.tz.FixedOffsetTimezone(offset=0, name=None))),
            (399541, u'Taylor Swift', 1, 3139, datetime.datetime(2011, 5, 16, 16, 32, 11, 963929, tzinfo=psycopg2.tz.FixedOffsetTimezone(offset=0, name=None))),
            (73502, u'Georg Friedrich Handel', 1, 27041, datetime.datetime(2011, 5, 16, 16, 32, 11, 963929, tzinfo=psycopg2.tz.FixedOffsetTimezone(offset=0, name=None))),
            (831440, u'George Frideric Handel', 1, 24955, datetime.datetime(2011, 6, 19, 7, 36, 56, 8576, tzinfo=psycopg2.tz.FixedOffsetTimezone(offset=0, name=None))),
            (847994, u'Handel', 1, 717, datetime.datetime(2011, 8, 11, 19, 43, 1, 279447, tzinfo=psycopg2.tz.FixedOffsetTimezone(offset=0, name=None))),
            (6747, u'Tampa Red', 1, 1600, datetime.datetime(2011, 5, 16, 16, 32, 11, 963929, tzinfo=psycopg2.tz.FixedOffsetTimezone(offset=0, name=None)))
        ]

        with db.engine.begin() as connection:
            db.import_mb_data.write_artist_credit(connection, data)
            self.assertEqual(data, db.import_mb_data.load_musicbrainz_schema_data(connection, 'artist_credit'))

        # release_group_primary_type
        data = [(1, u'Album', None, 1, None, uuid.UUID('f529b476-6e62-324f-b0aa-1f3e33d313fc'))]

        with db.engine.begin() as connection:
            db.import_mb_data.write_release_group_primary_type(connection, data)
            self.assertEqual(data, db.import_mb_data.load_musicbrainz_schema_data(connection, 'release_group_primary_type'))

        # release_group
        data = [(631361, uuid.UUID('2ec35fc4-6797-3324-b775-9a3df3d4723a'), u'The Masterworks', 73502, 1, u'', 0,
            datetime.datetime(2012, 5, 15, 19, 1, 58, 718541, tzinfo=psycopg2.tz.FixedOffsetTimezone(offset=0, name=None))),
            (617137, uuid.UUID('c834f5ee-d362-3da7-966b-8915a86e808c'), u'1981-08-29: Tangerine Tree Volume 53: Berlin 1981', 1418, 1, u'', 0,
            datetime.datetime(2016, 9, 21, 23, 0, 26, 94608, tzinfo=psycopg2.tz.FixedOffsetTimezone(offset=0, name=None)))
        ]

        with db.engine.begin() as connection:
            db.import_mb_data.write_release_group(connection, data)
            self.assertEqual(data, db.import_mb_data.load_musicbrainz_schema_data(connection, 'release_group'))

        # language
        data = [(120, u'eng', u'eng', u'en', u'English', 2, None)]

        with db.engine.begin() as connection:
            db.import_mb_data.write_language(connection, data)
            self.assertEqual(data, db.import_mb_data.load_musicbrainz_schema_data(connection, 'language'))

        # release_status
        data = [(1, u'Official', None, 1, u'Any release officially sanctioned by the artist and/or their record company. Most releases will fit into this category.',
            uuid.UUID('4e304316-386d-3409-af2e-78857eec5cfe'))]

        with db.engine.begin() as connection:
            db.import_mb_data.write_release_status(connection, data)
            self.assertEqual(data, db.import_mb_data.load_musicbrainz_schema_data(connection, 'release_status'))

        # release_packaging
        data = [(1, u'Jewel Case', None, 0, u'The traditional CD case, made of hard, brittle plastic.',
            uuid.UUID('ec27701a-4a22-37f4-bfac-6616e0f9750a'))
        ]

        with db.engine.begin() as connection:
            db.import_mb_data.write_release_packaging(connection, data)
            self.assertEqual(data, db.import_mb_data.load_musicbrainz_schema_data(connection, 'release_packaging'))

        # script
        data = [(28, u'Latn', u'215', u'Latin', 4)]

        with db.engine.begin() as connection:
            db.import_mb_data.write_script(connection, data)
            self.assertEqual(data, db.import_mb_data.load_musicbrainz_schema_data(connection, 'script'))

        # release
        data = [(692283, uuid.UUID('a830f892-6be0-35f0-a392-b91d89d89a94'), u'The Masterworks', 847994, 631361, 1, None, 120, 28, u'5028421923901', u'', 0, -1,
            datetime.datetime(2018, 5, 13, 11, 0, 22, 832493, tzinfo=psycopg2.tz.FixedOffsetTimezone(offset=0, name=None)))
        ]

        with db.engine.begin() as connection:
            db.import_mb_data.write_release(connection, data)
            self.assertEqual(data, db.import_mb_data.load_musicbrainz_schema_data(connection, 'release'))

        # medium
        data = [(1089027, 692283, 20, 1, u'Rinaldo, Part 1', 0, datetime.datetime(2011, 10, 24, 21, 0, 13, 19209, tzinfo=psycopg2.tz.FixedOffsetTimezone(offset=0, name=None)), 21)]

        with db.engine.begin() as connection:
            db.import_mb_data.write_medium(connection, data)
            self.assertEqual(data, db.import_mb_data.load_musicbrainz_schema_data(connection, 'medium'))


    def test_and_write_track(self):

        # artist_credit
        data = [(1418, u'Tangerine Dream', 1, 13729, datetime.datetime(2011, 5, 16, 16, 32, 11, 963929, tzinfo=psycopg2.tz.FixedOffsetTimezone(offset=0, name=None))),
            (399541, u'Taylor Swift', 1, 3139, datetime.datetime(2011, 5, 16, 16, 32, 11, 963929, tzinfo=psycopg2.tz.FixedOffsetTimezone(offset=0, name=None))),
            (73502, u'Georg Friedrich Handel', 1, 27041, datetime.datetime(2011, 5, 16, 16, 32, 11, 963929, tzinfo=psycopg2.tz.FixedOffsetTimezone(offset=0, name=None))),
            (831440, u'George Frideric Handel', 1, 24955, datetime.datetime(2011, 6, 19, 7, 36, 56, 8576, tzinfo=psycopg2.tz.FixedOffsetTimezone(offset=0, name=None))),
            (847994, u'Handel', 1, 717, datetime.datetime(2011, 8, 11, 19, 43, 1, 279447, tzinfo=psycopg2.tz.FixedOffsetTimezone(offset=0, name=None))),
            (6747, u'Tampa Red', 1, 1600, datetime.datetime(2011, 5, 16, 16, 32, 11, 963929, tzinfo=psycopg2.tz.FixedOffsetTimezone(offset=0, name=None)))
        ]

        with db.engine.begin() as connection:
            db.import_mb_data.write_artist_credit(connection, data)
            self.assertEqual(data, db.import_mb_data.load_musicbrainz_schema_data(connection, 'artist_credit'))

        # recording
        data = [(11768371, uuid.UUID('d51cf7fb-97e1-4070-a40b-b03707f91c92'), u'(Rinaldo, HWV 7: Act I. "Combatti da forte" (Almirena)', 73502, 203000, u'', 0, None, False),
            (8598260, uuid.UUID('9086b742-358b-4f73-9a14-84cb1a9ce4ce'), u'Love Story', 399541, 235000, u'', 0, None, False)
        ]

        with db.engine.begin() as connection:
            db.import_mb_data.write_recording(connection, data)
            self.assertEqual(data, db.import_mb_data.load_musicbrainz_schema_data(connection, 'recording'))

        # medium_format
        data = [(1, u'CD', None, 0, 1982, True, None, uuid.UUID('9712d52a-4509-3d4b-a1a2-67c88c643e31'))]

        with db.engine.begin() as connection:
            db.import_mb_data.write_medium_format(connection, data)
            self.assertEqual(data, db.import_mb_data.load_musicbrainz_schema_data(connection, 'medium_format'))

        # release_group_primary_type
        data = [(1, u'Album', None, 1, None, uuid.UUID('f529b476-6e62-324f-b0aa-1f3e33d313fc'))]

        with db.engine.begin() as connection:
            db.import_mb_data.write_release_group_primary_type(connection, data)
            self.assertEqual(data, db.import_mb_data.load_musicbrainz_schema_data(connection, 'release_group_primary_type'))

        # release_group
        data = [(631361, uuid.UUID('2ec35fc4-6797-3324-b775-9a3df3d4723a'), u'The Masterworks', 73502, 1, u'', 0,
            datetime.datetime(2012, 5, 15, 19, 1, 58, 718541, tzinfo=psycopg2.tz.FixedOffsetTimezone(offset=0, name=None))),
            (617137, uuid.UUID('c834f5ee-d362-3da7-966b-8915a86e808c'), u'1981-08-29: Tangerine Tree Volume 53: Berlin 1981', 1418, 1, u'', 0,
            datetime.datetime(2016, 9, 21, 23, 0, 26, 94608, tzinfo=psycopg2.tz.FixedOffsetTimezone(offset=0, name=None)))
        ]

        with db.engine.begin() as connection:
            db.import_mb_data.write_release_group(connection, data)
            self.assertEqual(data, db.import_mb_data.load_musicbrainz_schema_data(connection, 'release_group'))

        # language
        data = [(120, u'eng', u'eng', u'en', u'English', 2, None)]

        with db.engine.begin() as connection:
            db.import_mb_data.write_language(connection, data)
            self.assertEqual(data, db.import_mb_data.load_musicbrainz_schema_data(connection, 'language'))

        # release_status
        data = [(1, u'Official', None, 1, u'Any release officially sanctioned by the artist and/or their record company. Most releases will fit into this category.',
            uuid.UUID('4e304316-386d-3409-af2e-78857eec5cfe'))]

        with db.engine.begin() as connection:
            db.import_mb_data.write_release_status(connection, data)
            self.assertEqual(data, db.import_mb_data.load_musicbrainz_schema_data(connection, 'release_status'))

        # release_packaging
        data = [(1, u'Jewel Case', None, 0, u'The traditional CD case, made of hard, brittle plastic.',
            uuid.UUID('ec27701a-4a22-37f4-bfac-6616e0f9750a'))
        ]

        with db.engine.begin() as connection:
            db.import_mb_data.write_release_packaging(connection, data)
            self.assertEqual(data, db.import_mb_data.load_musicbrainz_schema_data(connection, 'release_packaging'))

        # script
        data = [(28, u'Latn', u'215', u'Latin', 4)]

        with db.engine.begin() as connection:
            db.import_mb_data.write_script(connection, data)
            self.assertEqual(data, db.import_mb_data.load_musicbrainz_schema_data(connection, 'script'))

        # release
        data = [(692283, uuid.UUID('a830f892-6be0-35f0-a392-b91d89d89a94'), u'The Masterworks', 847994, 631361, 1, None, 120, 28, u'5028421923901', u'', 0, -1,
            datetime.datetime(2018, 5, 13, 11, 0, 22, 832493, tzinfo=psycopg2.tz.FixedOffsetTimezone(offset=0, name=None)))
        ]

        with db.engine.begin() as connection:
            db.import_mb_data.write_release(connection, data)
            self.assertEqual(data, db.import_mb_data.load_musicbrainz_schema_data(connection, 'release'))

        # medium
        data = [(1089027, 692283, 20, 1, u'Rinaldo, Part 1', 0, datetime.datetime(2011, 10, 24, 21, 0, 13, 19209, tzinfo=psycopg2.tz.FixedOffsetTimezone(offset=0, name=None)), 21)]

        with db.engine.begin() as connection:
            db.import_mb_data.write_medium(connection, data)
            self.assertEqual(data, db.import_mb_data.load_musicbrainz_schema_data(connection, 'medium'))

        # track
        data = [(11261020, uuid.UUID('e0537cb9-4720-3eb3-a07a-d8a7477519ea'), 11768371, 1089027, 5, u'5', u'Rinaldo, HWV 7: Act I. "Combatti da forte" (Almirena)',
            831440, 203000, 0, datetime.datetime(2013, 7, 13, 11, 0, 38, 285946, tzinfo=psycopg2.tz.FixedOffsetTimezone(offset=0, name=None)), False)]

        with db.engine.begin() as connection:
            db.import_mb_data.write_track(connection, data)
            self.assertEqual(data, db.import_mb_data.load_musicbrainz_schema_data(connection, 'track'))


    def test_load_and_write_track_gid_redirect(self):
        # artist_credit
        data = [(1418, u'Tangerine Dream', 1, 13729, datetime.datetime(2011, 5, 16, 16, 32, 11, 963929, tzinfo=psycopg2.tz.FixedOffsetTimezone(offset=0, name=None))),
            (399541, u'Taylor Swift', 1, 3139, datetime.datetime(2011, 5, 16, 16, 32, 11, 963929, tzinfo=psycopg2.tz.FixedOffsetTimezone(offset=0, name=None))),
            (73502, u'Georg Friedrich Handel', 1, 27041, datetime.datetime(2011, 5, 16, 16, 32, 11, 963929, tzinfo=psycopg2.tz.FixedOffsetTimezone(offset=0, name=None))),
            (831440, u'George Frideric Handel', 1, 24955, datetime.datetime(2011, 6, 19, 7, 36, 56, 8576, tzinfo=psycopg2.tz.FixedOffsetTimezone(offset=0, name=None))),
            (847994, u'Handel', 1, 717, datetime.datetime(2011, 8, 11, 19, 43, 1, 279447, tzinfo=psycopg2.tz.FixedOffsetTimezone(offset=0, name=None))),
            (6747, u'Tampa Red', 1, 1600, datetime.datetime(2011, 5, 16, 16, 32, 11, 963929, tzinfo=psycopg2.tz.FixedOffsetTimezone(offset=0, name=None)))
        ]

        with db.engine.begin() as connection:
            db.import_mb_data.write_artist_credit(connection, data)
            self.assertEqual(data, db.import_mb_data.load_musicbrainz_schema_data(connection, 'artist_credit'))

        # recording
        data = [(11768371, uuid.UUID('d51cf7fb-97e1-4070-a40b-b03707f91c92'), u'(Rinaldo, HWV 7: Act I. "Combatti da forte" (Almirena)', 73502, 203000, u'', 0, None, False),
            (8598260, uuid.UUID('9086b742-358b-4f73-9a14-84cb1a9ce4ce'), u'Love Story', 399541, 235000, u'', 0, None, False)
        ]

        with db.engine.begin() as connection:
            db.import_mb_data.write_recording(connection, data)
            self.assertEqual(data, db.import_mb_data.load_musicbrainz_schema_data(connection, 'recording'))

        # medium_format
        data = [(1, u'CD', None, 0, 1982, True, None, uuid.UUID('9712d52a-4509-3d4b-a1a2-67c88c643e31'))]

        with db.engine.begin() as connection:
            db.import_mb_data.write_medium_format(connection, data)
            self.assertEqual(data, db.import_mb_data.load_musicbrainz_schema_data(connection, 'medium_format'))

        # release_group_primary_type
        data = [(1, u'Album', None, 1, None, uuid.UUID('f529b476-6e62-324f-b0aa-1f3e33d313fc'))]

        with db.engine.begin() as connection:
            db.import_mb_data.write_release_group_primary_type(connection, data)
            self.assertEqual(data, db.import_mb_data.load_musicbrainz_schema_data(connection, 'release_group_primary_type'))

        # release_group
        data = [(631361, uuid.UUID('2ec35fc4-6797-3324-b775-9a3df3d4723a'), u'The Masterworks', 73502, 1, u'', 0,
            datetime.datetime(2012, 5, 15, 19, 1, 58, 718541, tzinfo=psycopg2.tz.FixedOffsetTimezone(offset=0, name=None))),
            (617137, uuid.UUID('c834f5ee-d362-3da7-966b-8915a86e808c'), u'1981-08-29: Tangerine Tree Volume 53: Berlin 1981', 1418, 1, u'', 0,
            datetime.datetime(2016, 9, 21, 23, 0, 26, 94608, tzinfo=psycopg2.tz.FixedOffsetTimezone(offset=0, name=None)))
        ]

        with db.engine.begin() as connection:
            db.import_mb_data.write_release_group(connection, data)
            self.assertEqual(data, db.import_mb_data.load_musicbrainz_schema_data(connection, 'release_group'))

        # language
        data = [(120, u'eng', u'eng', u'en', u'English', 2, None)]

        with db.engine.begin() as connection:
            db.import_mb_data.write_language(connection, data)
            self.assertEqual(data, db.import_mb_data.load_musicbrainz_schema_data(connection, 'language'))

        # release_status
        data = [(1, u'Official', None, 1, u'Any release officially sanctioned by the artist and/or their record company. Most releases will fit into this category.',
            uuid.UUID('4e304316-386d-3409-af2e-78857eec5cfe'))]

        with db.engine.begin() as connection:
            db.import_mb_data.write_release_status(connection, data)
            self.assertEqual(data, db.import_mb_data.load_musicbrainz_schema_data(connection, 'release_status'))

        # release_packaging
        data = [(1, u'Jewel Case', None, 0, u'The traditional CD case, made of hard, brittle plastic.',
            uuid.UUID('ec27701a-4a22-37f4-bfac-6616e0f9750a'))
        ]

        with db.engine.begin() as connection:
            db.import_mb_data.write_release_packaging(connection, data)
            self.assertEqual(data, db.import_mb_data.load_musicbrainz_schema_data(connection, 'release_packaging'))

        # script
        data = [(28, u'Latn', u'215', u'Latin', 4)]

        with db.engine.begin() as connection:
            db.import_mb_data.write_script(connection, data)
            self.assertEqual(data, db.import_mb_data.load_musicbrainz_schema_data(connection, 'script'))

        # release
        data = [(692283, uuid.UUID('a830f892-6be0-35f0-a392-b91d89d89a94'), u'The Masterworks', 847994, 631361, 1, None, 120, 28, u'5028421923901', u'', 0, -1,
            datetime.datetime(2018, 5, 13, 11, 0, 22, 832493, tzinfo=psycopg2.tz.FixedOffsetTimezone(offset=0, name=None)))
        ]

        with db.engine.begin() as connection:
            db.import_mb_data.write_release(connection, data)
            self.assertEqual(data, db.import_mb_data.load_musicbrainz_schema_data(connection, 'release'))

        # medium
        data = [(1089027, 692283, 20, 1, u'Rinaldo, Part 1', 0, datetime.datetime(2011, 10, 24, 21, 0, 13, 19209, tzinfo=psycopg2.tz.FixedOffsetTimezone(offset=0, name=None)), 21)]

        with db.engine.begin() as connection:
            db.import_mb_data.write_medium(connection, data)
            self.assertEqual(data, db.import_mb_data.load_musicbrainz_schema_data(connection, 'medium'))

        # track
        data = [(11261020, uuid.UUID('e0537cb9-4720-3eb3-a07a-d8a7477519ea'), 11768371, 1089027, 5, u'5', u'Rinaldo, HWV 7: Act I. "Combatti da forte" (Almirena)',
            831440, 203000, 0, datetime.datetime(2013, 7, 13, 11, 0, 38, 285946, tzinfo=psycopg2.tz.FixedOffsetTimezone(offset=0, name=None)), False)]

        with db.engine.begin() as connection:
            db.import_mb_data.write_track(connection, data)
            self.assertEqual(data, db.import_mb_data.load_musicbrainz_schema_data(connection, 'track'))

        # track_gid_redirect
        data = [(uuid.UUID('67a0d0cd-fd61-328d-80a2-ca888c5fd15c'), 11261020, datetime.datetime(2014, 10, 15, 0, 0, 9, 772435, tzinfo=psycopg2.tz.FixedOffsetTimezone(offset=0, name=None)))]

        with db.engine.begin() as connection:
            db.import_mb_data.write_track_gid_redirect(connection, data)
            self.assertEqual(data, db.import_mb_data.load_musicbrainz_schema_data(connection, 'track_gid_redirect'))


    # def test_write_artist_type(self):

    # def test_write_area_type(self):

    # def test_write_release_status(self):

    # def test_write_release_group_primary_type(self):

    # def test_write_medium_format(self):

    # def test_write_release_packaging(self):

    # def test_write_language(self):

    # def test_write_script(self):

    # def test_write_gender(self):

    # def test_write_area_type_and_area(self):

    # def test_write_artist_type_and_artist_and_artist_gid_redirect(self):

    # def test_write_artist_credit_name(self):

    # def test_write_artist_gid_redirect(self):

    # def test_write_recording(sel

    # def test_write_release(self):

    # def test_write_release_gid_redirect(self):

    # def test_write_release_group_gid_redirect(self):

    # def test_write_track(self):

    # def test_write_track_gid_redirect(self):

    # def test_write_medium(self):
