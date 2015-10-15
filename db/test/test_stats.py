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
            m = uuid.uuid4()
            mbids.append(m)
            data = {"metadata":
                        {"tags": {"musicbrainz_recordingid": str(m), "artist": ["artist-%s"%i], "title": ["title-%s"%i]},
                         "audio_properties": {"lossless": True},
                         "version": {"essentia_build_sha": "sha"}}
                    }
            db.data.write_low_level(m, data)
        last = db.stats.get_last_submitted_recordings()
        dbget.assert_called_with("last-submitted-data")

        expected = [(mbids[9], "artist-9", "title-9"),
                    (mbids[8], "artist-8", "title-8"),
                    (mbids[7], "artist-7", "title-7"),
                    (mbids[6], "artist-6", "title-6"),
                    (mbids[5], "artist-5", "title-5")
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
