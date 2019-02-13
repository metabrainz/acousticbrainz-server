from db.testing import DatabaseTestCase


class ServerTestCase(DatabaseTestCase):

    def temporary_login(self, user_id):
        with self.client.session_transaction() as session:
            session['user_id'] = user_id
            session['_fresh'] = True
