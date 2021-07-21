from webserver.testing import AcousticbrainzTestCase
import unittest
import uuid
import mock
import datetime
import pytz
from sqlalchemy import text

from db import gid_types
import db.submission_stats
import db.data
import db


class SubmissionStatsTestCase(unittest.TestCase):
    """Statistics methods which use mocked database methods for testing"""

    def test_get_next_day(self):
        date1 = datetime.datetime(2016, 1, 7, 10, 20, 39, tzinfo=pytz.utc)
        next_day = db.submission_stats._get_next_day(date1)
        expected = datetime.datetime(2016, 1, 8, 0, 0, 0, tzinfo=pytz.utc)
        self.assertEqual(next_day, expected)

        # midnight on one day goes forward to midnight the next day
        date2 = datetime.datetime(2016, 1, 7, 0, 0, 0, tzinfo=pytz.utc)
        next_day = db.submission_stats._get_next_day(date2)
        expected = datetime.datetime(2016, 1, 8, 0, 0, 0, tzinfo=pytz.utc)
        self.assertEqual(next_day, expected)

    @mock.patch("db.submission_stats._get_stats_from_cache")
    @mock.patch("db.submission_stats.load_statistics_data")
    def test_get_stats_summary(self, load_stats, from_cache):
        # No cache and no database, return blank
        from_cache.return_value = (None, None)
        load_stats.return_value = []

        stats, last_collected = db.submission_stats.get_stats_summary()
        self.assertIsNone(last_collected)
        expected = {"lowlevel-lossy": 0, "lowlevel-lossy-unique": 0, "lowlevel-lossless": 0,
                    "lowlevel-lossless-unique": 0, "lowlevel-total": 0, "lowlevel-total-unique": 0}
        self.assertEquals(expected, stats)

        # No cache and yes database, return db
        from_cache.return_value = (None, None)
        load_stats.return_value = [{"collected": "date", "stats": "stats"}]

        stats, last_collected = db.submission_stats.get_stats_summary()
        self.assertEquals("date", last_collected)
        self.assertEquals("stats", stats)

        # if cache, return cache
        from_cache.return_value = ("cachedate", "cachestats")
        load_stats.return_value = [{"collected": "date", "stats": "stats"}]

        stats, last_collected = db.submission_stats.get_stats_summary()
        self.assertEquals("cachedate", last_collected)
        self.assertEquals("cachestats", stats)

    @mock.patch("brainzutils.cache.get")
    def test_get_stats_from_cache(self, cacheget):

        # magicmocks have all properties set to non-null, but timezone.localize
        # in _get_stats_from_cache checks this field to see if it's naive or not.
        # Explicitly set it to None so that 'localize' succeeds and the date is converted
        mockdt = mock.MagicMock()
        mockdt.tzinfo = None
        cacheget.side_effect = [mock.MagicMock(), mockdt]
        db.submission_stats._get_stats_from_cache()
        getcalls = [mock.call("recent-stats", namespace="statistics"),
                    mock.call("recent-stats-last-updated", namespace="statistics")]
        cacheget.assert_has_calls(getcalls)

    @mock.patch("db.engine.connect")
    @mock.patch("db.submission_stats._count_submissions_to_date")
    @mock.patch("db.submission_stats.datetime")
    @mock.patch("brainzutils.cache.set")
    def test_add_stats_to_cache(self, cacheset, dt, count, connect):
        datetimenow = datetime.datetime(2015, 12, 22, 14, 00, 00, tzinfo=pytz.utc)
        dt.datetime.now.return_value = datetimenow
        connection = "CONNECTION"
        connect.return_value.__enter__ = mock.Mock(return_value=connection)
        connect.return_value.__exit__ = mock.Mock(return_value=True)
        stats = {"stats": "here"}
        count.return_value = stats

        db.submission_stats.add_stats_to_cache()

        count.assert_called_once_with(connection, datetimenow)
        connect.assert_called_once_with()
        dt.datetime.now.assert_called_once_with(pytz.utc)
        setcalls = [mock.call("recent-stats", {"stats": "here"}, time=3600, namespace="statistics"),
                    mock.call("recent-stats-last-updated", datetimenow, time=3600, namespace="statistics")]
        cacheset.assert_has_calls(setcalls)


class SubmissionStatsDatabaseTestCase(AcousticbrainzTestCase):
    """Statistics methods which read and write from/to the database"""

    def setUp(self):
        super(SubmissionStatsDatabaseTestCase, self).setUp()

    @mock.patch("brainzutils.cache.get")
    @mock.patch("brainzutils.cache.set")
    def test_get_last_submitted_recordings(self, dbset, dbget):
        dbget.return_value = None
        mbids = []
        for i in range(20):
            rand_mbid = uuid.uuid4()
            mbids.append(str(rand_mbid))
            data = {
                "metadata": {
                    "tags": {
                        "musicbrainz_recordingid": str(rand_mbid),
                        "artist": ["artist-%s" % i],
                        "title": ["title-%s" % i],
                    },
                    "audio_properties": {"lossless": True},
                    "version": {"essentia_build_sha": "sha"},
                },
            }
            db.data.write_low_level(rand_mbid, data, gid_types.GID_TYPE_MBID)
        last = db.submission_stats.get_last_submitted_recordings()
        dbget.assert_called_with("last-submitted-recordings")

        expected = [
            {"mbid": mbids[9], "artist": "artist-9", "title": "title-9"},
            {"mbid": mbids[8], "artist": "artist-8", "title": "title-8"},
            {"mbid": mbids[7], "artist": "artist-7", "title": "title-7"},
            {"mbid": mbids[6], "artist": "artist-6", "title": "title-6"},
            {"mbid": mbids[5], "artist": "artist-5", "title": "title-5"},
        ]
        self.assertEqual(expected, last)

    def test_count_submissions_to_date(self):
        """If we add some items, we can count them"""
        date1 = datetime.datetime(2016, 1, 7, 10, 20, 39, tzinfo=pytz.utc)
        date2 = datetime.datetime(2016, 1, 7, 12, 30, 20, tzinfo=pytz.utc)
        date3 = datetime.datetime(2016, 1, 8, 1, 00, 00, tzinfo=pytz.utc)
        date4 = datetime.datetime(2016, 1, 10, 1, 00, 00, tzinfo=pytz.utc)
        add_empty_lowlevel(uuid.uuid4(), True, date1)
        two_uuid = uuid.uuid4()
        add_empty_lowlevel(two_uuid, True, date2)
        three_uuid = uuid.uuid4()
        # Same uuid should appear as 1 less unique
        add_empty_lowlevel(three_uuid, False, date3)
        add_empty_lowlevel(three_uuid, False, date4)
        add_empty_lowlevel(three_uuid, True, date4)
        add_empty_lowlevel(two_uuid, True, date4)

        with db.engine.connect() as connection:
            two_submissions_date = datetime.datetime(2016, 1, 7, 15, 00, 00, tzinfo=pytz.utc)
            three_submissions_date = datetime.datetime(2016, 1, 9, 15, 00, 00, tzinfo=pytz.utc)
            five_submissions_date = datetime.datetime(2016, 1, 10, 15, 00, 00, tzinfo=pytz.utc)
            ret = db.submission_stats._count_submissions_to_date(connection, two_submissions_date)
            self.assertEqual({'lowlevel-lossless': 2,
                              'lowlevel-lossless-unique': 2,
                              'lowlevel-lossy': 0,
                              'lowlevel-lossy-unique': 0,
                              'lowlevel-total': 2,
                              'lowlevel-total-unique': 2}, ret)

            ret = db.submission_stats._count_submissions_to_date(connection, three_submissions_date)
            self.assertEqual({'lowlevel-lossless': 2,
                              'lowlevel-lossless-unique': 2,
                              'lowlevel-lossy': 1,
                              'lowlevel-lossy-unique': 1,
                              'lowlevel-total': 3,
                              'lowlevel-total-unique': 3}, ret)

            ret = db.submission_stats._count_submissions_to_date(connection, five_submissions_date)
            self.assertEqual({'lowlevel-lossless': 4,
                              'lowlevel-lossless-unique': 3,
                              'lowlevel-lossy': 2,
                              'lowlevel-lossy-unique': 1,
                              'lowlevel-total': 6,
                              'lowlevel-total-unique': 3}, ret)

    def test_get_most_recent_stats_date(self):
        """Get the most recent date that we have for stats"""
        date = datetime.datetime(2016, 01, 10, 00, 00, tzinfo=pytz.utc)
        stats = {'lowlevel-lossless': 2,
                 'lowlevel-lossless-unique': 2,
                 'lowlevel-lossy': 0,
                 'lowlevel-lossy-unique': 0,
                 'lowlevel-total': 2,
                 'lowlevel-total-unique': 2}
        with db.engine.connect() as connection:
            db.submission_stats._write_stats(connection, date, stats)

            res_date = db.submission_stats._get_most_recent_stats_date(connection)
            self.assertEqual(res_date, date)

    def test_write_and_get_statistics_data(self):
        stats1 = {"lowlevel-lossy": 10, "lowlevel-lossy-unique": 6,
                  "lowlevel-lossless": 15, "lowlevel-lossless-unique": 10,
                  "lowlevel-total": 25, "lowlevel-total-unique": 16}
        date1 = datetime.datetime(2016, 01, 10, 00, 00, tzinfo=pytz.utc)
        stats2 = {"lowlevel-lossy": 15, "lowlevel-lossy-unique": 10,
                  "lowlevel-lossless": 20, "lowlevel-lossless-unique": 10,
                  "lowlevel-total": 35, "lowlevel-total-unique": 20}
        date2 = datetime.datetime(2016, 01, 11, 00, 00, tzinfo=pytz.utc)
        with db.engine.connect() as connection:
            db.submission_stats._write_stats(connection, date1, stats1)
            db.submission_stats._write_stats(connection, date2, stats2)

        data = db.submission_stats.load_statistics_data()
        self.assertEqual(2, len(data))
        expected_data = [
            {"collected": date1, "stats": stats1},
            {"collected": date2, "stats": stats2}
        ]
        self.assertEqual(list(expected_data), list(data))

    def test_write_stats_error(self):
        """Test that we can generate highcharts format, even if some
           data is missing for a date."""

        date1 = datetime.datetime(2016, 1, 10, 00, 00, tzinfo=pytz.utc)
        stats1 = {"lowlevel-lossy": 10, "lowlevel-lossy-unique": 6,
                  "lowlevel-lossless": 15, "lowlevel-lossless-unique": "not-a-number",
                  "lowlevel-total": 25, "lowlevel-total-unique": 16}

        with self.assertRaises(ValueError):
            with db.engine.connect() as connection:
                db.submission_stats._write_stats(connection, date1, stats1)

        stats2 = {"lowlevel-lossy": 15, "lowlevel-lossy-unique": 10,
                  "lowlevel-lossless": 20,  # missing lowlevel-lossless-unique
                  "lowlevel-total": 35, "lowlevel-total-unique": 20}
        date2 = datetime.datetime(2016, 1, 11, 00, 00, tzinfo=pytz.utc)
        with self.assertRaises(ValueError):
            with db.engine.connect() as connection:
                db.submission_stats._write_stats(connection, date2, stats2)

    def test_format_statistics_for_hicharts(self):
        """Format statistics for display on history graph"""

        stats1 = {"lowlevel-lossy": 10, "lowlevel-lossy-unique": 6,
                  "lowlevel-lossless": 15, "lowlevel-lossless-unique": 10,
                  "lowlevel-total": 25, "lowlevel-total-unique": 16}
        date1 = datetime.datetime(2016, 01, 10, 00, 00, tzinfo=pytz.utc)
        stats2 = {"lowlevel-lossy": 15, "lowlevel-lossy-unique": 10,
                  "lowlevel-lossless": 20, "lowlevel-lossless-unique": 10,
                  "lowlevel-total": 35, "lowlevel-total-unique": 20}
        date2 = datetime.datetime(2016, 01, 11, 00, 00, tzinfo=pytz.utc)
        data = [
            {"collected": date1, "stats": stats1},
            {"collected": date2, "stats": stats2}
        ]

        formatted = db.submission_stats.format_statistics_for_highcharts(data)
        expected_formatted = [
            {'data': [[1452384000000, 15], [1452470400000, 20]], 'name': 'Lossless (all)'},
            {'data': [[1452384000000, 10], [1452470400000, 10]], 'name': 'Lossless (unique)'},
            {'data': [[1452384000000, 10], [1452470400000, 15]], 'name': 'Lossy (all)'},
            {'data': [[1452384000000, 6], [1452470400000, 10]], 'name': 'Lossy (unique)'},
            {'data': [[1452384000000, 25], [1452470400000, 35]], 'name': 'Total (all)'},
            {'data': [[1452384000000, 16], [1452470400000, 20]], 'name': 'Total (unique)'}]
        self.assertEqual(sorted(expected_formatted), sorted(formatted))

    def test_get_statistics_data_limit(self):
        stats1 = {"lowlevel-lossy": 10, "lowlevel-lossy-unique": 6,
                  "lowlevel-lossless": 15, "lowlevel-lossless-unique": 10,
                  "lowlevel-total": 25, "lowlevel-total-unique": 16}
        date1 = datetime.datetime(2016, 01, 10, 00, 00, tzinfo=pytz.utc)
        stats2 = {"lowlevel-lossy": 15, "lowlevel-lossy-unique": 10,
                  "lowlevel-lossless": 20, "lowlevel-lossless-unique": 10,
                  "lowlevel-total": 35, "lowlevel-total-unique": 20}
        date2 = datetime.datetime(2016, 01, 11, 00, 00, tzinfo=pytz.utc)
        with db.engine.connect() as connection:
            db.submission_stats._write_stats(connection, date1, stats1)
            db.submission_stats._write_stats(connection, date2, stats2)

        # If we ask for just 1 stats, it's the one that's later in time
        data = db.submission_stats.load_statistics_data(1)
        self.assertEqual(1, len(data))
        expected_data = [
            {"collected": date2, "stats": stats2}
        ]
        self.assertEqual(list(expected_data), list(data))

    def test_get_earliest_submission_date(self):
        # If nothing is in the database, the date should be None
        with db.engine.connect() as connection:
            earliest_date = db.submission_stats._get_earliest_submission_date(connection)
            self.assertIsNone(earliest_date)

            # otherwise, the first submitted date
            date1 = datetime.datetime(2016, 01, 07, 10, 20, 39, tzinfo=pytz.utc)
            date2 = datetime.datetime(2016, 01, 07, 12, 30, 20, tzinfo=pytz.utc)
            add_empty_lowlevel(uuid.uuid4(), True, date1)
            add_empty_lowlevel(uuid.uuid4(), True, date2)

            earliest_date = db.submission_stats._get_earliest_submission_date(connection)
            self.assertEqual(earliest_date, date1)


def add_empty_lowlevel(mbid, lossless, date):
    build_sha1 = "sha1"
    # sha256 field must be unique
    data_sha256 = str(lossless) + str(mbid) + str(date)
    data_sha256 = data_sha256[:64]
    data_json = "{}"
    gid_type = gid_types.GID_TYPE_MSID
    with db.engine.connect() as connection:
        query = text("""
            SELECT MAX(submission_offset)
              FROM lowlevel
             WHERE gid::text = :mbid
        """)
        result = connection.execute(query, {"mbid": str(mbid)})
        row = result.fetchone()
        if row[0] is not None:
            submission_offset = row[0] + 1
        else:
            submission_offset = 0

        query = text("""
            INSERT INTO lowlevel (gid, build_sha1, lossless, submitted, gid_type, submission_offset)
                 VALUES (:mbid, :build_sha1, :lossless, :submitted, :gid_type, :submission_offset)
              RETURNING id
        """)
        result = connection.execute(query,
                                    {"mbid": mbid, "build_sha1": build_sha1,
                                     "lossless": lossless, "submitted": date,
                                     "gid_type": gid_types.GID_TYPE_MSID,
                                     "submission_offset": submission_offset})
        id = result.fetchone()[0]

        version_id = db.data.insert_version(connection, {}, db.data.VERSION_TYPE_LOWLEVEL)
        query = text("""
          INSERT INTO lowlevel_json (id, data, data_sha256, version)
               VALUES (:id, :data, :data_sha256, :version)
        """)
        connection.execute(query,
                           {"id": id, "data": data_json,
                            "data_sha256": data_sha256, "version": version_id})


class SubmissionStatsHighchartsTestCase(AcousticbrainzTestCase):
    """Statistics methods which test the graphs on the website"""

    def setUp(self):
        super(SubmissionStatsHighchartsTestCase, self).setUp()

    def test_get_statistics_history(self):
        """Test that we can generate highcharts format."""
        stats1 = {"lowlevel-lossy": 10, "lowlevel-lossy-unique": 6,
                  "lowlevel-lossless": 15, "lowlevel-lossless-unique": 10,
                  "lowlevel-total": 25, "lowlevel-total-unique": 16}
        date1 = datetime.datetime(2016, 1, 10, 00, 00, tzinfo=pytz.utc)
        stats2 = {"lowlevel-lossy": 15, "lowlevel-lossy-unique": 10,
                  "lowlevel-lossless": 20, "lowlevel-lossless-unique": 10,
                  "lowlevel-total": 35, "lowlevel-total-unique": 20}
        date2 = datetime.datetime(2016, 1, 11, 00, 00, tzinfo=pytz.utc)
        with db.engine.connect() as connection:
            db.submission_stats._write_stats(connection, date1, stats1)
            db.submission_stats._write_stats(connection, date2, stats2)

        history = db.submission_stats.get_statistics_history()
        # 6 data types
        self.assertEqual(len(history), 6)
        # each item has 2 dates
        for h in history:
            self.assertEqual(len(h["data"]), 2)
        # Example of date conversion
        self.assertEqual(history[0], {"data": [[1452384000000, 15], [1452470400000, 20]], "name": "Lossless (all)"})

    @mock.patch("db.submission_stats._get_stats_from_cache")
    def test_stats_cache(self, get_stats_from_cache):
        """If there are stats calculated and stored in the cache since the last time
        they were added to the database, also include them"""

        stats = {"lowlevel-lossy": 10, "lowlevel-lossy-unique": 6,
                 "lowlevel-lossless": 15, "lowlevel-lossless-unique": 10,
                 "lowlevel-total": 25, "lowlevel-total-unique": 16}
        date = datetime.datetime(2016, 1, 10, 00, 00, tzinfo=pytz.utc)
        date2 = datetime.datetime(2016, 1, 11, 00, 00, tzinfo=pytz.utc)
        with db.engine.connect() as connection:
            db.submission_stats._write_stats(connection, date, stats)
            db.submission_stats._write_stats(connection, date2, stats)

        # No items returned from cache, don't add anything
        get_stats_from_cache.return_value = (None, None)
        history = db.submission_stats.get_statistics_history()
        # 6 data types
        self.assertEqual(len(history), 6)
        # each item has 2 dates
        for h in history:
            self.assertEqual(len(h["data"]), 2)

        # Cache item is earlier than most recent database value, don't add anything
        datecache = datetime.datetime(2016, 1, 10, 22, 0, tzinfo=pytz.utc)
        get_stats_from_cache.return_value = (datecache, stats)
        history = db.submission_stats.get_statistics_history()
        self.assertEqual(len(history[0]["data"]), 2)

        # Cache item is later than most recent database value, add it to the stats
        datecache = datetime.datetime(2016, 1, 11, 1, 0, tzinfo=pytz.utc)
        get_stats_from_cache.return_value = (datecache, stats)
        history = db.submission_stats.get_statistics_history()
        # Each item now has 3 dates
        for h in history:
            self.assertEqual(len(h["data"]), 3)
