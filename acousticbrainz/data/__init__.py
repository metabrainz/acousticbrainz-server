import psycopg2
import logging

# Be careful when importing `_connection` before init_connection function is
# called! In general helper functions like `create_cursor` or `commit` should
# be used. Feel free to add new ones if some functionality is missing.
_connection = None


def create_cursor():
    """Creates a new psycopg `cursor` object.

    See http://initd.org/psycopg/docs/connection.html#connection.cursor.
    """
    return _connection.cursor()


def commit():
    """Commits any pending transaction to the database.

    See http://initd.org/psycopg/docs/connection.html#connection.commit.
    """
    return _connection.commit()


def init_connection(dsn):
    global _connection
    try:
        _connection = psycopg2.connect(dsn)
    except psycopg2.OperationalError as e:
        logging.error("Failed to initialize database connection: %s" % str(e))


def run_sql_script(sql_file_path):
    global _connection
    with _connection.cursor() as cursor:
        with open(sql_file_path) as sql:
            cursor.execute(sql.read())
