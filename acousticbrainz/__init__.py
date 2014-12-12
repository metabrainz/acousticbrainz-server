from flask import Flask
from flask_uuid import FlaskUUID
import logging
from logging.handlers import RotatingFileHandler

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

    # Extensions
    FlaskUUID(app)

    # Blueprints
    from acousticbrainz.views.index import index_bp
    from acousticbrainz.views.data import data_bp
    from acousticbrainz.views.stats import stats_bp

    app.register_blueprint(index_bp)
    app.register_blueprint(data_bp)
    app.register_blueprint(stats_bp)

    from acousticbrainz.views.data import init_websocket
    init_websocket(app)

    return app
