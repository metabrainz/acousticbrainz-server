import unittest

from unittest import mock
from flask import url_for
from flask_login import login_required, AnonymousUserMixin
from werkzeug.exceptions import BadRequest, InternalServerError, NotFound

import db.user as db_user
import webserver.login
from webserver import create_app
from webserver.testing import AcousticbrainzTestCase


class IndexViewsTestCase(AcousticbrainzTestCase):

    def test_index(self):
        resp = self.client.get(url_for('index.index'))
        self.assert200(resp)

    def test_downloads(self):
        resp = self.client.get(url_for('index.downloads'))
        self.assert200(resp)

    def test_contribute(self):
        resp = self.client.get(url_for('index.contribute'))
        self.assert200(resp)

    def test_goals(self):
        resp = self.client.get(url_for('index.goals'))
        self.assert200(resp)

    def test_faq(self):
        resp = self.client.get(url_for('index.faq'))
        self.assert200(resp)

    def test_flask_debugtoolbar(self):
        """ Test if flask debugtoolbar is loaded correctly

        Creating an app with default config so that debug is True
        and SECRET_KEY is defined.
        """
        app = create_app(debug=True)
        client = app.test_client()
        resp = client.get(url_for('index.goals'))
        self.assert200(resp)
        self.assertIn('flDebug', str(resp.data))

    @mock.patch('db.user.get')
    def test_menu_not_logged_in(self, mock_user_get):
        resp = self.client.get(url_for('index.index'))
        data = resp.data.decode('utf-8')
        self.assertIn('Sign in', data)
        # item in user menu doesn't exist
        self.assertNotIn('Your profile', data)
        mock_user_get.assert_not_called()

    @mock.patch('db.user.get')
    def test_menu_logged_in(self, mock_user_get):
        """ If the user is logged in, check that we perform a database query to get user data """
        user = db_user.get_or_create('little_rsh')
        db_user.agree_to_gdpr(user['musicbrainz_id'])
        user = db_user.get_or_create('little_rsh')
        mock_user_get.return_value = user
        self.temporary_login(user['id'])
        resp = self.client.get(url_for('index.index'))
        data = resp.data.decode('utf-8')

        # username (menu header)
        self.assertIn('little_rsh', data)
        # item in user menu
        self.assertIn('Your profile', data)
        mock_user_get.assert_called_with(user['id'])

    @mock.patch('db.user.get')
    def test_menu_logged_in_error_show(self, mock_user_get):
        """ If the user is logged in, if we show a 400 or 404 error, show the user menu"""
        @self.app.route('/page_that_returns_400')
        def view400():
            raise BadRequest('bad request')

        @self.app.route('/page_that_returns_404')
        def view404():
            raise NotFound('not found')

        user = db_user.get_or_create('little_rsh')
        db_user.agree_to_gdpr(user['musicbrainz_id'])
        user = db_user.get_or_create('little_rsh')
        mock_user_get.return_value = user
        self.temporary_login(user['id'])
        resp = self.client.get('/page_that_returns_400')
        data = resp.data.decode('utf-8')
        self.assert400(resp)

        # username (menu header)
        self.assertIn('little_rsh', data)
        # item in user menu
        self.assertIn('Your profile', data)
        mock_user_get.assert_called_with(user['id'])

        resp = self.client.get('/page_that_returns_404')
        data = resp.data.decode('utf-8')
        self.assert404(resp)
        # username (menu header)
        self.assertIn('little_rsh', data)
        # item in user menu
        self.assertIn('Your profile', data)
        mock_user_get.assert_called_with(user['id'])

    @unittest.skip('GDPR @before_request forces user.get to always happen, before errors could happen')
    @mock.patch('db.user.get')
    def test_menu_logged_in_error_dont_show_no_user(self, mock_user_get):
        """ If the user is logged in, if we show a 500 error, do not show the user menu
            Don't query the database to get a current_user for the template context"""
        @self.app.route('/page_that_returns_500')
        def view500():
            raise InternalServerError('error')

        user = db_user.get_or_create('little_rsh')
        mock_user_get.return_value = user
        self.temporary_login(user['id'])
        resp = self.client.get('/page_that_returns_500')
        data = resp.data.decode('utf-8')
        # item not in user menu
        self.assertNotIn('Your profile', data)
        self.assertIn('Sign in', data)
        mock_user_get.assert_not_called()
        self.assertIsInstance(self.get_context_variable('current_user'), AnonymousUserMixin)

    @mock.patch('db.user.get')
    def test_menu_logged_in_error_dont_show_user_loaded(self, mock_user_get):
        """ If the user is logged in, if we show a 500 error, do not show the user menu
        If the user has previously been loaded in the view, check that it's not
        loaded while rendering the template"""

        user = db_user.get_or_create('little_rsh')
        db_user.agree_to_gdpr(user['musicbrainz_id'])
        user = db_user.get_or_create('little_rsh')
        mock_user_get.return_value = user

        @self.app.route('/page_that_returns_500')
        @login_required
        def view500():
            # flask-login user is loaded during @login_required, so check that the db has been queried
            mock_user_get.assert_called_with(user['id'])
            raise InternalServerError('error')

        self.temporary_login(user['id'])
        resp = self.client.get('/page_that_returns_500')
        data = resp.data.decode('utf-8')
        # item not in user menu
        self.assertNotIn('Your profile', data)
        self.assertIn('Sign in', data)
        # Even after rendering the template, the database has only been queried once (before the exception)
        mock_user_get.assert_called_once_with(user['id'])
        self.assertIsInstance(self.get_context_variable('current_user'), webserver.login.User)

    def test_gdpr_redirect(self):
        """Test that a user who logs in and hasn't agreed to the GDPR terms
        gets redirected to the preferences page"""

        user = db_user.get_or_create('newuser')
        self.temporary_login(user['id'])
        resp = self.client.get(url_for('index.index'))
        self.assertStatus(resp, 302)
        self.assertIn(url_for('index.gdpr_notice'), resp.location)

        # User accepts
        db_user.agree_to_gdpr(user['musicbrainz_id'])
        resp = self.client.get(url_for('index.index'))
        self.assert200(resp)
        self.assertIsNone(resp.location)