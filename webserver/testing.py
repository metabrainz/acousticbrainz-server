from db.testing import DatabaseTestCase
import os

TEST_DATA_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'views', 'test_data')

class ServerTestCase(DatabaseTestCase):

    def temporary_login(self, user_id):
        with self.client.session_transaction() as session:
            session['user_id'] = user_id
            session['_fresh'] = True
