DEBUG = False
TESTING = True

SECRET_KEY = "CHANGE_ME"

# Test database
SQLALCHEMY_DATABASE_URI = "postgresql://ab_test@db/ab_test"
POSTGRES_ADMIN_AB_URI = "postgresql://postgres@db/ab_test"


# MUSICBRAINZ
# MUSICBRAINZ_USERAGENT = "acousticbrainz-server"
MUSICBRAINZ_HOSTNAME = None

# OAuth
MUSICBRAINZ_CLIENT_ID = "CLIENT_ID"
MUSICBRAINZ_CLIENT_SECRET = "CLIENT_SECRET"

# LOGGING

#LOG_FILE_ENABLED = True
#LOG_FILE = "./acousticbrainz.log"

#LOG_EMAIL_ENABLED = True
#LOG_EMAIL_TOPIC = "AcousticBrainz Webserver Failure"
#LOG_EMAIL_RECIPIENTS = []  # List of email addresses (strings)

#LOG_SENTRY_ENABLED = True
#SENTRY_DSN = ""


# MISCELLANEOUS

# Mail server
# These variables need to be defined if you enabled log emails.
#SMTP_SERVER = "localhost"
#SMTP_PORT = 25
#MAIL_FROM_DOMAIN = "acousticbrainz.org"

