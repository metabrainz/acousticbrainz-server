import db
import db.exceptions
import sqlalchemy
import string
import random
from six.moves import range

KEY_LENGTH = 40


def generate(owner_id):
    """Generate new key for a specified user.

    Doesn't check if user exists.

    Args:
        owner_id: ID of a user that will be associated with a key.

    Returns:
        Value of the new key.
    """
    with db.engine.connect() as connection:
        value = _generate_key(KEY_LENGTH)
        connection.execute(sqlalchemy.text("""
            INSERT INTO api_key (value, owner)
                 VALUES (:value, :owner)
        """), {
            "value": value,
            "owner": owner_id
        })
        return value


def get_active(owner_id):
    """Get active keys for a user.

    Doesn't check if user exists.

    Args:
        owner_id: ID of a user who owns the key.

    Returns:
        List of active API keys.
    """
    with db.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text("""
            SELECT value
              FROM api_key
             WHERE owner = :owner
        """), {"owner": owner_id})
        return [row["value"] for row in result.fetchall()]


def revoke(value):
    """Revoke key with a given value."""
    with db.engine.connect() as connection:
        connection.execute(sqlalchemy.text("""
            UPDATE api_key
               SET is_active = FALSE
             WHERE value = :value
        """), {"value": value})


def revoke_all(owner_id):
    """Revoke all keys owned by a user."""
    with db.engine.connect() as connection:
        connection.execute(sqlalchemy.text("""
            UPDATE api_key
               SET is_active = FALSE
             WHERE owner = :owner
        """), {"owner": owner_id})


def is_active(value):
    """Check if key is active.

    Args:
        value: Value of a key.

    Returns:
        True if key is active, False if it's not.

    Raises:
        NoDataFoundException: Specified key was not found.
    """
    with db.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text("""
            SELECT is_active
              FROM api_key
             WHERE value = :value
        """), {"value": value})
        row = result.fetchone()
        if not row:
            raise db.exceptions.NoDataFoundException("Can't find specified API key.")
        return row["is_active"]


def _generate_key(length):
    """Generates random string with a specified length."""
    return ''.join(random.SystemRandom().choice(string.ascii_letters + string.digits)
                   for _ in range(length))
