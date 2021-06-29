from __future__ import print_function

from brainzutils.flask import CustomFlask
from brainzutils.ratelimit import set_rate_limits, inject_x_rate_headers
from flask import request, url_for, redirect
from flask_login import current_user
from pprint import pprint

import os
import time
from six.moves import urllib

API_PREFIX = '/api/'

# Check to see if we're running under a docker deployment. If so, don't second guess
# the config file setup and just wait for the correct configuration to be generated.
deploy_env = os.environ.get('DEPLOY_ENV', '')
CONSUL_CONFIG_FILE_RETRY_COUNT = 10


def create_app_flaskgroup(script_info):
    """Factory function that accepts script_info and creates a Flask application"""
    return create_app(debug=True)


def load_config(app):
    """Load configuration file for specified Flask app"""
    config_file = os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "config.py")
    if deploy_env:
        for _ in range(CONSUL_CONFIG_FILE_RETRY_COUNT):
            if not os.path.exists(config_file):
                time.sleep(1)

        if not os.path.exists(config_file):
            print("No config file generated. Retried %d times, exiting." % CONSUL_CONFIG_FILE_RETRY_COUNT)

    app.config.from_pyfile(config_file)

    if deploy_env:
        print('Config file loaded!')
        pprint(dict(app.config))


def create_app(debug=None):
    app = CustomFlask(
        import_name=__name__,
        use_flask_uuid=True,
    )

    # Configuration
    load_config(app)

    if debug is not None:
        app.debug = debug

    if app.debug and app.config['SECRET_KEY']:
        app.init_debug_toolbar()

    # Logging
    app.init_loggers(file_config=app.config.get('LOG_FILE'),
                     sentry_config=app.config.get('LOG_SENTRY')
                     )

    # Database connection
    from db import init_db_engine
    init_db_engine(app.config['SQLALCHEMY_DATABASE_URI'])

    # Cache
    if 'REDIS_HOST' in app.config and\
       'REDIS_PORT' in app.config and\
       'REDIS_NAMESPACE' in app.config and\
       'REDIS_NS_VERSIONS_LOCATION' in app.config:
        if not os.path.exists(app.config['REDIS_NS_VERSIONS_LOCATION']):
            os.makedirs(app.config['REDIS_NS_VERSIONS_LOCATION'])

        from brainzutils import cache
        cache.init(
            host=app.config['REDIS_HOST'],
            port=app.config['REDIS_PORT'],
            namespace=app.config['REDIS_NAMESPACE'],
            ns_versions_loc=app.config['REDIS_NS_VERSIONS_LOCATION'])
    else:
        raise Exception('One or more redis cache configuration options are missing from config.py')

    # Add rate limiting support
    @app.after_request
    def after_request_callbacks(response):
        return inject_x_rate_headers(response)

    # check for ratelimit config values and set them if present
    if 'RATELIMIT_PER_IP' in app.config and 'RATELIMIT_WINDOW' in app.config:
        set_rate_limits(app.config['RATELIMIT_PER_IP'], app.config['RATELIMIT_PER_IP'], app.config['RATELIMIT_WINDOW'])

    # MusicBrainz
    import musicbrainzngs
    from db import SCHEMA_VERSION
    musicbrainzngs.set_useragent(app.config['MUSICBRAINZ_USERAGENT'], SCHEMA_VERSION)
    if app.config['MUSICBRAINZ_HOSTNAME']:
        musicbrainzngs.set_hostname(app.config['MUSICBRAINZ_HOSTNAME'])

    # OAuth
    from webserver.login import login_manager, provider
    login_manager.init_app(app)
    provider.init(app.config['MUSICBRAINZ_CLIENT_ID'],
                  app.config['MUSICBRAINZ_CLIENT_SECRET'])

    # Error handling
    from webserver.errors import init_error_handlers
    init_error_handlers(app)

    # Static files
    from webserver import static_manager

    # Template utilities
    app.jinja_env.add_extension('jinja2.ext.do')
    from webserver import utils
    app.jinja_env.filters['date'] = utils.reformat_date
    app.jinja_env.filters['datetime'] = utils.reformat_datetime
    # During development, built js and css assets don't have a hash, but in production we use
    # a manifest to map a name to name.hash.extension for caching/cache busting
    if app.debug:
        app.context_processor(lambda: dict(get_static_path=static_manager.development_get_static_path))
    else:
        static_manager.read_manifest()
        app.context_processor(lambda: dict(get_static_path=static_manager.manifest_get_static_path))

    _register_blueprints(app)

    # Admin section
    from flask_admin import Admin
    from webserver.admin import views as admin_views
    admin = Admin(app, index_view=admin_views.HomeView(name='Admin'))
    admin.add_view(admin_views.AdminsView(name='Admins'))

    @app.before_request
    def prod_https_login_redirect():
        """ Redirect to HTTPS in production except for the API endpoints
        """
        if urllib.parse.urlsplit(request.url).scheme == 'http' \
                and app.config['DEBUG'] == False \
                and app.config['TESTING'] == False \
                and request.blueprint not in ('api', 'api_v1_core', 'api_v1_datasets', 'api_v1_dataset_eval'):
            url = request.url[7:] # remove http:// from url
            return redirect('https://{}'.format(url), 301)


    @app.before_request
    def before_request_gdpr_check():
        # skip certain pages, static content and the API
        if request.path == url_for('index.gdpr_notice') \
          or request.path == url_for('login.logout') \
          or request.path.startswith('/_debug') \
          or request.path.startswith('/static') \
          or request.path.startswith(API_PREFIX):
            return
        # otherwise if user is logged in and hasn't agreed to gdpr,
        # redirect them to agree to terms page.
        elif current_user.is_authenticated and current_user.gdpr_agreed is None:
            return redirect(url_for('index.gdpr_notice', next=request.full_path))

    return app


def create_app_sphinx():
    """Creates application for generating the documentation using Sphinx.

    Read the Docs builder doesn't have a database or any other custom software
    that we use, so we have to ignore these initialization steps. Only
    blueprints/views are needed to build documentation.
    """
    app = CustomFlask(import_name=__name__, use_flask_uuid=True)
    _register_blueprints(app)
    return app


def _register_blueprints(app):

    def register_ui(app):
        from webserver.views.index import index_bp
        from webserver.views.data import data_bp
        from webserver.views.stats import stats_bp
        from webserver.views.login import login_bp
        from webserver.views.user import user_bp
        from webserver.views.datasets import datasets_bp
        app.register_blueprint(index_bp)
        app.register_blueprint(data_bp)
        app.register_blueprint(stats_bp)
        app.register_blueprint(login_bp, url_prefix='/login')
        app.register_blueprint(user_bp)
        app.register_blueprint(datasets_bp, url_prefix='/datasets')

    def register_api(app):
        v1_prefix = os.path.join(API_PREFIX, 'v1')
        from webserver.views.api.v1.core import bp_core
        from webserver.views.api.v1.datasets import bp_datasets
        from webserver.views.api.v1.dataset_eval import bp_dataset_eval
        app.register_blueprint(bp_core, url_prefix=v1_prefix)
        app.register_blueprint(bp_datasets, url_prefix=v1_prefix + '/datasets')
        app.register_blueprint(bp_dataset_eval, url_prefix=v1_prefix + '/datasets/evaluation')

        from webserver.views.api.legacy import api_legacy_bp
        app.register_blueprint(api_legacy_bp)

    register_ui(app)
    register_api(app)
