import psycopg2

# Be careful when importing this before init_connection function is called!
connection = None

def init_connection(dsn):
    global connection
    connection = psycopg2.connect(dsn)

def run_sql_script(sql_file_path):
    global connection
    with connection.cursor() as cursor:
        with open(sql_file_path) as sql:
            cursor.execute(sql.read())
