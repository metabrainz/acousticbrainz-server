from db.testing import DatabaseTestCase
import db.stats
import db.data
import uuid
import mock


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

    # @mock.patch("db.cache.get")
    # @mock.patch("db.cache.set")
    # def test_get_last_submitted_recordings_cached(self, dbget, dbset):
    #     pass

    # @mock.patch("db.cache.get")
    # @mock.patch("db.cache.set")
    # def test_get_last_submitted_recordings_bad_data(self, dbget, dbset):
    #    pass
