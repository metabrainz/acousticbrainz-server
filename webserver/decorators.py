from functools import update_wrapper, wraps
from datetime import timedelta
from flask import request, current_app, make_response
from flask_login import current_user
from six import string_types
from werkzeug.exceptions import Unauthorized

import db.user
from webserver.login import User
from webserver.views.api.exceptions import APIUnauthorized


def api_token_or_session_login_required(f):
    """Check if a request to an API method is authenticated, either with an existing
    session or with an Authorization header.
    In the case that this method is being called from the browser (e.g. the dataset editor),
    the user will be authorized. Call the view.

    In the case that there is no session authorization, check for the Authorization header and
    find a valid user. If this user exists, set flask_login's current_user to this user
    and call the view.

    If there is no session set and no header (or the header is invalid) return an Unauthorized
    exception formatted as json.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            auth_token = request.headers.get("Authorization")
            user = None
            if auth_token:
                parts = auth_token.split(" ")
                if len(parts) == 2 and parts[0] == "Token":
                    db_user = db.user.get_by_api_key(parts[1])
                    if db_user:
                        user = User.from_dbrow(db_user)
                        current_app.login_manager._update_request_context_with_user(user)
            if not user:
                raise APIUnauthorized("You need to provide an Authorization header.")

        return f(*args, **kwargs)
    return decorated


def service_session_login_required(f):
    """Require a 'service' api (API used by the website, but not available to external clients)
     to have a valid session authorization.
     The session is logged in with the standard flask_login user_loader.
     If the user isn't logged in, raise the standard flask Unauthorized exception.

     This is different to flask-login's @login_required in that it directly returns Unauthorized
     instead of redirecting the user to the login page.
     """
    @wraps(f)
    def decorated(*args, **kwargs):
        if current_user.is_authenticated:
            return f(*args, **kwargs)
        else:
            raise Unauthorized
    return decorated


def crossdomain(origin='*', methods=None, headers=None,
                max_age=21600, attach_to_all=True,
                automatic_options=True):
    # Based on snippet by Armin Ronacher located at http://flask.pocoo.org/snippets/56/.
    if methods is not None:
        methods = ', '.join(sorted(x.upper() for x in methods))
    if headers is not None and not isinstance(headers, string_types):
        headers = ', '.join(x.upper() for x in headers)
    if not isinstance(origin, string_types):
        origin = ', '.join(origin)
    if isinstance(max_age, timedelta):
        max_age = max_age.total_seconds()

    def get_methods():
        if methods is not None:
            return methods

        options_resp = current_app.make_default_options_response()
        return options_resp.headers['allow']

    def decorator(f):
        def wrapped_function(*args, **kwargs):
            if automatic_options and request.method == 'OPTIONS':
                resp = current_app.make_default_options_response()
            else:
                resp = make_response(f(*args, **kwargs))
            if not attach_to_all and request.method != 'OPTIONS':
                return resp

            h = resp.headers

            h['Access-Control-Allow-Origin'] = origin
            h['Access-Control-Allow-Methods'] = get_methods()
            h['Access-Control-Max-Age'] = str(max_age)
            if headers is not None:
                h['Access-Control-Allow-Headers'] = headers
            return resp

        f.provide_automatic_options = False
        return update_wrapper(wrapped_function, f)
    return decorator
