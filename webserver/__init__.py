from flask import Flask
import sys
import os


def create_app():
    app = Flask(__name__)

    # Configuration
    sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), ".."))
    import config
    app.config.from_object(config)

    # Logging
    from webserver.loggers import init_loggers
    init_loggers(app)

    # Database connection
    from db import init_db_engine
    init_db_engine(app.config['SQLALCHEMY_DATABASE_URI'])

    # Memcached
    if 'MEMCACHED_SERVERS' in app.config:
        from db import cache
        cache.init(app.config['MEMCACHED_SERVERS'],
                   app.config['MEMCACHED_NAMESPACE'],
                   debug=1 if app.debug else 0)

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

    # Blueprints
    from webserver.views.index import index_bp
    from webserver.views.data import data_bp
    from webserver.views.api import api_bp
    from webserver.views.stats import stats_bp
    from webserver.views.login import login_bp
    from webserver.views.user import user_bp
    from webserver.views.datasets import datasets_bp
    from webserver.views.challenges import challenges_bp
    app.register_blueprint(index_bp)
    app.register_blueprint(data_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(stats_bp)
    app.register_blueprint(login_bp, url_prefix='/login')
    app.register_blueprint(user_bp)
    app.register_blueprint(datasets_bp, url_prefix='/datasets')
    app.register_blueprint(challenges_bp, url_prefix='/challenges')

    # Admin section
    from flask_admin import Admin
    from webserver.admin.views import home, admins, challenges
    admin = Admin(app, index_view=home.HomeView(name='Home'))
    admin.add_view(admins.AdminsView(name='Admins'))
    admin.add_view(challenges.ChallengesView(name='Challenges'))

    return app
