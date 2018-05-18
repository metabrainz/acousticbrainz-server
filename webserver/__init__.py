from brainzutils.flask import CustomFlask
import os

API_PREFIX = '/api/'

def create_app_flaskgroup(script_info):
    """Factory function that accepts script_info and creates a Flask application"""
    return create_app()


def create_app_with_configuration(config_path=None):
    """Create a Flask application and load all configuration files"""

    app = CustomFlask(
        import_name=__name__,
        use_flask_uuid=True,
    )

    # Configuration
    root_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "..")
    app.config.from_pyfile(os.path.join(
        root_path,
        'default_config.py'
    ))
    app.config.from_pyfile(os.path.join(
        root_path,
        'custom_config.py'
    ), silent=True)

    if config_path:
        app.config.from_pyfile(config_path)

    return app


def create_app(debug=None, config_path=None):
    app = create_app_with_configuration(config_path)

    if debug is not None:
        app.debug = debug

    if app.debug and app.config['SECRET_KEY']:
        app.init_debug_toolbar()

    # Logging
    from webserver.loggers import init_loggers
    init_loggers(app)

    # Database connection
    from db import init_db_engine
    init_db_engine(app.config['SQLALCHEMY_DATABASE_URI'])

    # MusicBrainz Database
    from brainzutils import musicbrainz_db
    musicbrainz_db.init_db_engine(app.config.get('MB_DATABASE_URI'))

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
        raise Exception('One or more redis cache configuration options are missing from custom_config.py')

    # Extensions
    from flask_uuid import FlaskUUID
    FlaskUUID(app)

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
    import static_manager
    static_manager.read_manifest()

    # Template utilities
    app.jinja_env.add_extension('jinja2.ext.do')
    from webserver import utils
    app.jinja_env.filters['date'] = utils.reformat_date
    app.jinja_env.filters['datetime'] = utils.reformat_datetime
    app.context_processor(lambda: dict(get_static_path=static_manager.get_static_path))

    _register_blueprints(app)

    # Admin section
    from flask_admin import Admin
    from webserver.admin import views as admin_views
    admin = Admin(app, index_view=admin_views.HomeView(name='Admin'))
    admin.add_view(admin_views.AdminsView(name='Admins'))

    return app


def create_app_sphinx():
    """Creates application for generating the documentation using Sphinx.

    Read the Docs builder doesn't have a database or any other custom software
    that we use, so we have to ignore these initialization steps. Only
    blueprints/views are needed to build documentation.
    """
    app = CustomFlask(import_name=__name__)
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
