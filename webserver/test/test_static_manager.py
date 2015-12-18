from webserver.testing import ServerTestCase
from webserver import static_manager


class StaticManagerTestCase(ServerTestCase):

    def test_get_file_path(self):
        self.assertEqual(static_manager.get_file_path("script.js"), "/static/script.js")
        self.assertEqual(static_manager.get_file_path("img/test.png"), "/static/img/test.png")
