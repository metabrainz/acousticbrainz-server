from __future__ import print_function
from flask_script import Manager, Server
from flask import current_app
from web_server import data
from web_server.data.dump_manager import manager as dump_manager
from web_server.data.dump import import_db_dump
from web_server import create_app
import subprocess
import os

manager = Manager(create_app)

manager.add_command('runserver', Server(host='0.0.0.0', port=8080))
manager.add_command('dump', dump_manager)


ADMIN_SQL_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'admin', 'sql')


@manager.command
def init_db(archive=None, force=False):
    """Initializes database and imports data if needed.

    This process involves several steps:
    1. Table structure is created.
    2. Data is imported from the archive if it is specified.
    3. Primary keys and foreign keys are created.
    3. Indexes are created.

    Data dump needs to be a .tar.xz archive produced by export command.

    More information about populating a PostgreSQL database efficiently can be
    found at http://www.postgresql.org/docs/current/static/populate.html.
    """
    if force:
        exit_code = subprocess.call('sudo -u postgres psql < ' +
                                    os.path.join(ADMIN_SQL_DIR, 'drop_db.sql'),
                                    shell=True)
        if exit_code != 0:
            raise Exception('Failed to drop existing database and user! Exit code: %i' % exit_code)

    print('Creating user and a database...')
    exit_code = subprocess.call('sudo -u postgres psql < ' +
                                os.path.join(ADMIN_SQL_DIR, 'create_db.sql'),
                                shell=True)
    if exit_code != 0:
        raise Exception('Failed to create new database and user! Exit code: %i' % exit_code)

    print('Creating database extensions...')
    exit_code = subprocess.call('sudo -u postgres psql -d acousticbrainz < ' +
                                os.path.join(ADMIN_SQL_DIR, 'create_extensions.sql'),
                                shell=True)
    if exit_code != 0:
        raise Exception('Failed to create database extensions! Exit code: %i' % exit_code)

    data.init_connection(current_app.config['PG_CONNECT'])

    print('Creating tables...')
    data.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'create_tables.sql'))

    import_data(archive) if archive else print('Skipping data importing.')

    print('Creating primary and foreign keys...')
    data.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'create_primary_keys.sql'))
    data.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'create_foreign_keys.sql'))

    print('Creating indexes...')
    data.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'create_indexes.sql'))

    print("Done!")


@manager.command
def init_test_db(force=False):
    """Same as `init_db`, but creates a database that will be used to run tests
    and doesn't import data (no need to do that).
    """
    if force:
        exit_code = subprocess.call('sudo -u postgres psql < ' +
                                    os.path.join(ADMIN_SQL_DIR, 'drop_test_db.sql'),
                                    shell=True)
        if exit_code != 0:
            raise Exception('Failed to drop existing database and user! Exit code: %i' % exit_code)

    print('Creating database and user for testing...')
    exit_code = subprocess.call('sudo -u postgres psql < ' +
                                os.path.join(ADMIN_SQL_DIR, 'create_test_db.sql'),
                                shell=True)
    if exit_code != 0:
        raise Exception('Failed to create new database and user! Exit code: %i' % exit_code)

    exit_code = subprocess.call('sudo -u postgres psql -d ab_test < ' +
                                os.path.join(ADMIN_SQL_DIR, 'create_extensions.sql'),
                                shell=True)
    if exit_code != 0:
        raise Exception('Failed to create database extensions! Exit code: %i' % exit_code)

    current_app.config['PG_CONNECT'] = current_app.config['PG_CONNECT_TEST']
    data.init_connection(current_app.config['PG_CONNECT'])

    data.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'create_tables.sql'))
    data.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'create_primary_keys.sql'))
    data.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'create_foreign_keys.sql'))
    data.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'create_indexes.sql'))

    print("Done!")


@manager.command
def import_data(archive):
    print('Importing data...')
    import_db_dump(archive)


if __name__ == '__main__':
    manager.run()
