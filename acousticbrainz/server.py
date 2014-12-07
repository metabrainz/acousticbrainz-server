#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging
import config
from logging.handlers import RotatingFileHandler
from flask import Flask
import argparse


STATIC_PATH = "/static"
STATIC_FOLDER = "../static"
TEMPLATE_FOLDER = "../templates"

app = Flask(__name__,
            static_url_path = STATIC_PATH,
            static_folder = STATIC_FOLDER,
            template_folder = TEMPLATE_FOLDER)

# Configuration
app.config.from_object(config)

# Error handling and logging
handler = RotatingFileHandler(config.LOG_FILE)
handler.setLevel(logging.INFO)
app.logger.addHandler(handler)

# Blueprints
from views.index import index_bp
from views.data import data_bp
from views.stats import stats_bp

app.register_blueprint(index_bp)
app.register_blueprint(data_bp)
app.register_blueprint(stats_bp)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='AcousticBrainz dev server')
    parser.add_argument("-d", "--debug", help="Turn on debugging mode to see stack traces in the error pages", default=True, action='store_true')
    parser.add_argument("-t", "--host", help="Which interfaces to listen on. Default: 127.0.0.1", default="127.0.0.1", type=str)
    parser.add_argument("-p", "--port", help="Which port to listen on. Default: 8080", default="8080", type=int)
    args = parser.parse_args()
    app.run(debug=True, host=args.host, port=args.port)
