from flask import Flask
from logging.handlers import RotatingFileHandler
import logging
import sys

# This value must be incremented after schema changes on replicated tables!
__version__ = 2


def create_app():
    app = Flask(__name__)

    # Configuration
    sys.path.append("../")
    import config
    app.config.from_object(config)

    # Error handling and logging
    handler = RotatingFileHandler(app.config['LOG_FILE'])
    handler.setLevel(logging.INFO)
    app.logger.addHandler(handler)

    # Database connection
    from web_server import data
    data.init_connection(app.config['PG_CONNECT'])

    # Memcached
    if 'MEMCACHED_SERVERS' in app.config:
        from web_server import cache
        cache.init(app.config['MEMCACHED_SERVERS'],
                   app.config['MEMCACHED_NAMESPACE'],
                   debug=1 if app.debug else 0)

    # Extensions
    from flask_uuid import FlaskUUID
    FlaskUUID(app)

    # MusicBrainz
    import musicbrainzngs
    musicbrainzngs.set_useragent(app.config['MUSICBRAINZ_USERAGENT'], __version__)
    if app.config['MUSICBRAINZ_HOSTNAME']:
        musicbrainzngs.set_hostname(app.config['MUSICBRAINZ_HOSTNAME'])

    # OAuth
    from web_server.login import login_manager, provider
    login_manager.init_app(app)
    provider.init(app.config['MUSICBRAINZ_CLIENT_ID'],
                  app.config['MUSICBRAINZ_CLIENT_SECRET'])

    # Error handling
    from web_server.errors import init_error_handlers
    init_error_handlers(app)

    # Blueprints
    from web_server.views.index import index_bp
    from web_server.views.data import data_bp
    from web_server.views.api import api_bp
    from web_server.views.stats import stats_bp
    from web_server.views.login import login_bp
    from web_server.views.user import user_bp
    from web_server.views.datasets import datasets_bp
    app.register_blueprint(index_bp)
    app.register_blueprint(data_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(stats_bp)
    app.register_blueprint(login_bp, url_prefix='/login')
    app.register_blueprint(user_bp, url_prefix='/user')
    app.register_blueprint(datasets_bp, url_prefix='/datasets')

    return app
