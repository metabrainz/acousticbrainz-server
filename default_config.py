import os


DEBUG = False  # set to False in production mode
# Additional files to watch to restart the development server
RELOAD_ON_FILES = ["webserver/static/build/rev-manifest.json"]

SECRET_KEY = "CHANGE_ME"


# DATABASES

# Primary database
SQLALCHEMY_DATABASE_URI = "postgresql://acousticbrainz@db/acousticbrainz"

# URI to connect to an empty database as the superuser
POSTGRES_ADMIN_URI = "postgresql://postgres@db/template1"
# URI to connect to the acousticbrainz database as the superuser (to install extensions)
POSTGRES_ADMIN_AB_URI = "postgresql://postgres@db/acousticbrainz"

# MUSICBRAINZ

MUSICBRAINZ_USERAGENT = "acousticbrainz-server"
MUSICBRAINZ_HOSTNAME = None

# OAuth
MUSICBRAINZ_CLIENT_ID = "CHANGE_ME"
MUSICBRAINZ_CLIENT_SECRET = "CHANGE_ME"

# CACHE

REDIS_HOST = "redis"
REDIS_PORT = 6379
REDIS_NAMESPACE = "AB"
REDIS_NS_VERSIONS_LOCATION = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'cache_namespaces')

# LOGGING

LOG_FILE_ENABLED = False
LOG_FILE = "./acousticbrainz.log"

LOG_EMAIL_ENABLED = False
LOG_EMAIL_TOPIC = "AcousticBrainz Webserver Failure"
LOG_EMAIL_RECIPIENTS = []  # List of email addresses (strings)

LOG_SENTRY_ENABLED = False
SENTRY_DSN = ""


# MISCELLANEOUS

# Mail server
# These variables need to be defined if you enabled log emails.
SMTP_SERVER = "localhost"
SMTP_PORT = 25
MAIL_FROM_DOMAIN = "acousticbrainz.org"

FILE_STORAGE_DIR = "./files"

#Feature Flags
FEATURE_EVAL_LOCATION = False
