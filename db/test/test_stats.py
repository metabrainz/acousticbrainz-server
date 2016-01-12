from db.testing import DatabaseTestCase
import db
import db.stats
import db.data
import uuid
import mock
import datetime
import pytz
from sqlalchemy import text


class StatsTestCase(DatabaseTestCase):

    def setUp(self):
        super(StatsTestCase, self).setUp()

    @mock.patch("db.cache.get")
    @mock.patch("db.cache.set")
    def test_get_last_submitted_recordings(self, dbset, dbget):
        dbget.return_value = None
        mbids = []
        for i in range(20):
            rand_mbid = uuid.uuid4()
            mbids.append(rand_mbid)
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
            db.data.write_low_level(rand_mbid, data)
        last = db.stats.get_last_submitted_recordings()
        dbget.assert_called_with("last-submitted-recordings")

        expected = [
            {"mbid": mbids[9], "artist": "artist-9", "title": "title-9"},
            {"mbid": mbids[8], "artist": "artist-8", "title": "title-8"},
            {"mbid": mbids[7], "artist": "artist-7", "title": "title-7"},
            {"mbid": mbids[6], "artist": "artist-6", "title": "title-6"},
            {"mbid": mbids[5], "artist": "artist-5", "title": "title-5"},
        ]
        self.assertEqual(expected, last)

    def test_get_earliest_submission_date(self):
        # If nothing is in the database, the date should be None
        earliest_date = db.stats.get_earliest_submission_date()
        self.assertIsNone(earliest_date)

        # otherwise, the first submitted date
        date1 = datetime.datetime(2016, 01, 07, 10, 20, 39, tzinfo=pytz.utc)
        date2 = datetime.datetime(2016, 01, 07, 12, 30, 20, tzinfo=pytz.utc)
        add_empty_lowlevel(uuid.uuid4(), True, date1)
        add_empty_lowlevel(uuid.uuid4(), True, date2)

        earliest_date = db.stats.get_earliest_submission_date()
        self.assertEqual(earliest_date, date1)

    def test_get_next_hour(self):
        date1 = datetime.datetime(2016, 01, 07, 10, 20, 39, tzinfo=pytz.utc)
        next_hour = db.stats.get_next_hour(date1)
        expected = datetime.datetime(2016, 01, 07, 11, 0, 0, tzinfo=pytz.utc)
        self.assertEqual(next_hour, expected)

        date2 = datetime.datetime(2016, 01, 07, 13, 0, 0, tzinfo=pytz.utc)
        next_hour = db.stats.get_next_hour(date2)
        expected = datetime.datetime(2016, 01, 07, 14, 0, 0, tzinfo=pytz.utc)
        self.assertEqual(next_hour, expected)


def add_empty_lowlevel(mbid, lossless, date):
    build_sha1 = "sha1"
    # must be unique
    data_sha256 = "sha256" + str(mbid) + str(date)
    data_json = "{}"
    with db.engine.connect() as connection:
        q = text("""INSERT INTO lowlevel
            (mbid, build_sha1, data_sha256, lossless, data, submitted)
            VALUES (:mbid, :build_sha1, :data_sha256,
                    :lossless, :data, :submitted)""")
        connection.execute(q,
            {"mbid": mbid, "build_sha1": build_sha1,
                "data_sha256": data_sha256, "lossless": lossless,
                "data": data_json, "submitted": date}
        )

