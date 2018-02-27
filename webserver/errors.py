from flask import render_template, jsonify, request
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
        return render_template('errors/400.html', error=error, code = error.code), 400

    @app.errorhandler(401)
    def unauthorized(error):
        # always returning JSON because this is only raised from API endpoints
        return jsonify_error(error)
    
    @app.errorhandler(403)
    def forbidden(error):
        return render_template('errors/403.html', error=error, code = error.code), 403

    @app.errorhandler(404)
    def not_found(error):
        if request.path.startswith(webserver.API_PREFIX):
            return jsonify_error(error)
        return render_template('errors/404.html', error=error, code = error.code), 404

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
        return render_template('errors/500.html', error=error, code = error.code), 500

    @app.errorhandler(503)
    def service_unavailable(error):
        return render_template('errors/503.html', error=error, code = error.code), 503


def jsonify_error(error, code=None):
    if hasattr(error, 'description'):
        message = error.description
    else:
        message = str(error)
    api_error = api_exceptions.APIError(message, getattr(error, 'code', code))
    return jsonify(api_error.to_dict()), api_error.status_code
