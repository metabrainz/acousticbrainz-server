from flask import Flask
from flask_uuid import FlaskUUID
import logging
from logging.handlers import RotatingFileHandler

# This value must be incremented after schema changes on replicated tables!
__version__ = 2

STATIC_PATH = "/static"
STATIC_FOLDER = "../static"
TEMPLATE_FOLDER = "../templates"


def create_app():
    app = Flask(__name__,
                static_url_path=STATIC_PATH,
                static_folder=STATIC_FOLDER,
                template_folder=TEMPLATE_FOLDER)

    # Configuration
    app.config.from_object('acousticbrainz.config')

    # Error handling and logging
    handler = RotatingFileHandler(app.config['LOG_FILE'])
    handler.setLevel(logging.INFO)
    app.logger.addHandler(handler)

    # Database connection
    from acousticbrainz import data
    # FIXME(roman): This fails during testing if database referenced in PG_CONNECT doesn't exist.
    # TODO: It's probably good idea to check if PG_CONNECT is defined.
    data.init_connection(app.config['PG_CONNECT'])

    # Memcached
    if 'MEMCACHED_SERVERS' in app.config:
        from acousticbrainz import cache
        cache.init(app.config['MEMCACHED_SERVERS'],
                   app.config['MEMCACHED_NAMESPACE'],
                   debug=1 if app.debug else 0)

    # Extensions
    FlaskUUID(app)

    # MusicBrainz
    import musicbrainzngs
    musicbrainzngs.set_useragent(app.config['MUSICBRAINZ_USERAGENT'], __version__)
    if app.config['MUSICBRAINZ_HOSTNAME']:
        musicbrainzngs.set_hostname(app.config['MUSICBRAINZ_HOSTNAME'])

    # OAuth
    from acousticbrainz.login import login_manager, provider
    login_manager.init_app(app)
    provider.init(app.config['MUSICBRAINZ_CLIENT_ID'],
                  app.config['MUSICBRAINZ_CLIENT_SECRET'])

    # Error handling
    import errors
    errors.init_error_handlers(app)

    # Blueprints
    from acousticbrainz.views.index import index_bp
    from acousticbrainz.views.data import data_bp
    from acousticbrainz.views.api import api_bp
    from acousticbrainz.views.stats import stats_bp
    from acousticbrainz.views.login import login_bp
    from acousticbrainz.views.user import user_bp
    from acousticbrainz.views.datasets import datasets_bp

    app.register_blueprint(index_bp)
    app.register_blueprint(data_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(stats_bp)
    app.register_blueprint(login_bp, url_prefix='/login')
    app.register_blueprint(user_bp, url_prefix='/user')
    app.register_blueprint(datasets_bp, url_prefix='/datasets')

    return app
