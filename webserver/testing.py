from db.testing import DatabaseTestCase
import os
from brainzutils.ratelimit import set_rate_limits

TEST_DATA_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'views', 'test_data')


class ServerTestCase(DatabaseTestCase):

    def setUp(self):
        super(ServerTestCase, self).setUp()

        # TODO: https://tickets.metabrainz.org/browse/BU-27
        set_rate_limits(1000, 1000, 10000)

    def temporary_login(self, user_id):
        with self.client.session_transaction() as session:
            session['_user_id'] = user_id
            session['_fresh'] = True
