import psycopg2
import logging

_connection = None

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
