"""
Flask-UUID, a UUID url converter for Flask.
"""

import re
import uuid

from werkzeug.routing import BaseConverter, ValidationError


# The uuid.UUID() constructor accepts various formats, so use a strict
# regular expression to keep urls unique.
UUID_RE = re.compile(
    r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$')


class UUIDConverter(BaseConverter):
    """
    UUID converter for the Werkzeug routing system.
    """

    def __init__(self, map, strict=True):
        super(UUIDConverter, self).__init__(map)
        self.strict = strict

    def to_python(self, value):
        if self.strict and not UUID_RE.match(value):
            raise ValidationError()

        try:
            return uuid.UUID(value)
        except ValueError:
            raise ValidationError()

    def to_url(self, value):
        return str(value)


class FlaskUUID(object):
    """Flask extension providing a UUID url converter"""
    def __init__(self, app=None):
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        app.url_map.converters['uuid'] = UUIDConverter
