from webserver.testing import AcousticbrainzTestCase
from webserver import static_manager


class StaticManagerTestCase(AcousticbrainzTestCase):

    def test_get_static_path(self):
        self.assertEqual(static_manager.development_get_static_path("script.js"), "/static/script.js")
        self.assertEqual(static_manager.development_get_static_path("img/test.png"), "/static/img/test.png")

    def test_manifest_get_static_path(self):
        static_manager.manifest_content = {"somefile.js": "/static/build/somefile.hash.js"}
        self.assertEqual(static_manager.manifest_get_static_path("somefile.js"), "/static/build/somefile.hash.js")
        self.assertEqual(static_manager.manifest_get_static_path("img/test.png"), "/static/img/test.png")
