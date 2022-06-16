import six
from flask import render_template, jsonify, request, has_request_context, _request_ctx_stack, current_app

import webserver
from webserver.views.api import exceptions as api_exceptions


def init_error_handlers(app):

    @app.errorhandler(api_exceptions.APIError)
    def api_error(error):
        return jsonify(error.to_dict()), error.status_code

    @app.errorhandler(400)
    def bad_request(error):
        if request.path.startswith(webserver.API_PREFIX):
            return jsonify_error(error)
        return render_template('errors/400.html', error=error), 400

    @app.errorhandler(401)
    def unauthorized(error):
        # always returning JSON because this is only raised from API endpoints
        return jsonify_error(error)

    @app.errorhandler(403)
    def forbidden(error):
        return render_template('errors/403.html', error=error), 403

    @app.errorhandler(404)
    def not_found(error):
        if request.path.startswith(webserver.API_PREFIX):
            return jsonify_error(error)
        return render_template('errors/404.html', error=error), 404

    @app.errorhandler(429)
    def too_many_requests(error):
        # always returning JSON because this is only raised from API endpoints
        return jsonify_error(error, 429)

    @app.errorhandler(500)
    def internal_server_error(error):
        if request.path.startswith(webserver.API_PREFIX):
            # The error parameter here could be any Exception, not a nice
            # werkzeug exception like in other error handlers.
            # In the case of an exception in the API, we want a basic message
            # and no additional stuff (like a stack trace).
            # We assume that developers get reports through sentry/reporting emails
            error = Exception("An unknown error occurred")
            error.code = 500
            return jsonify_error(error)
        # On an HTTP500 page we want to make sure we don't do any more database queries
        # in case the error was caused by an un-rolled-back database exception.
        # flask-login will do a query to add `current_user` to the template if it's not
        # already in the request context, so we override it with AnonymousUser to prevent it from doing so
        # Ideally we wouldn't do this, and we would catch and roll back all database exceptions
        if has_request_context() and not hasattr(_request_ctx_stack.top, 'user'):
            _request_ctx_stack.top.user = current_app.login_manager.anonymous_user()
        hide_navbar_user_menu = True
        return render_template('errors/500.html', error=error, hide_navbar_user_menu=hide_navbar_user_menu), 500

    @app.errorhandler(503)
    def service_unavailable(error):
        return render_template('errors/503.html', error=error), 503


def jsonify_error(error, code=None):
    if hasattr(error, 'description'):
        message = error.description
    elif hasattr(error, 'error'):
        message = error.error
    elif len(error.args):
        message = six.ensure_text(error.args[0])
    else:
        message = "unknown error"
    api_error = api_exceptions.APIError(message, getattr(error, 'code', code))
    return jsonify(api_error.to_dict()), api_error.status_code
