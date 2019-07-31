import string
import random


def generate_string(length):
    """Generates random string with a specified length."""
    return ''.join([random.SystemRandom().choice(
        string.ascii_letters + string.digits
    ) for _ in range(length)])


def reformat_date(value, fmt="%b %d, %Y"):
    return value.strftime(fmt)


def reformat_datetime(value, fmt="%b %d, %Y, %H:%M %Z"):
    return value.strftime(fmt)

def _validate_offset(offset):
    """Validate the offset.

    If the offset is None, return 0, otherwise interpret it as a number. If it is
    not a number, raise 400.
    """
    if offset:
        try:
            offset = int(offset)
        except ValueError:
            raise webserver.views.api.exceptions.APIBadRequest("Offset must be an integer value")
    else:
        offset = 0
    return offset