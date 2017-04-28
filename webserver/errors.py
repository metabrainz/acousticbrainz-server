from flask import render_template, jsonify, request
from webserver.views.api import exceptions as api_exceptions


def init_error_handlers(app):

    @app.errorhandler(api_exceptions.APIError)
    def api_error(error):
        return jsonify(error.to_dict()), error.status_code

    @app.errorhandler(400)
    def bad_request(error):
        return render_template('errors/400.html', error=error), 400

    @app.errorhandler(401)
    def unauthorized(error):
        #always returning JSON, until we need a template for 401 error
        return jsonify_error(error)
    
    @app.errorhandler(403)
    def forbidden(error):
        return render_template('errors/403.html', error=error), 403

    @app.errorhandler(404)
    def not_found(error):
        if request.path.startswith('/api/v1/'):
            return jsonify_error(error)
        return render_template('errors/404.html', error=error), 404

    @app.errorhandler(500)
    def internal_server_error(error):
        if request.path.startswith('/api/v1/'):
            return jsonify_error(error)
        return render_template('errors/500.html', error=error), 500

    @app.errorhandler(503)
    def service_unavailable(error):
        return render_template('errors/503.html', error=error), 503

def jsonify_error(error):
    api_error = api_exceptions.APIError(error.description, error.code)
    return jsonify(api_error.to_dict()), api_error.status_code
