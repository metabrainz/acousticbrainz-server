from __future__ import print_function
from flask_script import Manager, Server
from flask import current_app
from acousticbrainz.data.dump_manager import manager as dump_manager
from acousticbrainz.data.dump import import_db_dump
from acousticbrainz.data import run_sql_script
from acousticbrainz import create_app
import subprocess
import os

manager = Manager(create_app)

manager.add_command('dump', dump_manager)

manager.add_command("runserver", Server(host="0.0.0.0", port=8080))

@manager.command
def init_db(archive=None, force=False):
    """Initializes database and imports data if needed.

    This process involves several steps:
    1. Table structure is created.
    2. Data is imported from the archive if it is specified.
    3. Primary keys and foreign keys are created.
    3. Indexes are created.

    Data dump needs to be a .tar.xz archive produced by export command.

    More information about populating a PostgreSQL database efficently can be
    found at http://www.postgresql.org/docs/current/static/populate.html.
    """
    if force:
        exit_code = subprocess.call('sudo -u postgres psql < ' +
                                    os.path.join('admin', 'sql', 'drop_db.sql'),
                                    shell=True)
        if exit_code != 0:
            raise Exception('Failed to drop existing database and user! Exit code: %i' % exit_code)

    print('Creating user and a database...')
    exit_code = subprocess.call('sudo -u postgres psql < ' +
                                os.path.join('admin', 'sql', 'create_db.sql'),
                                shell=True)
    if exit_code != 0:
        raise Exception('Failed to new database and user! Exit code: %i' % exit_code)

    print('Creating tables...')
    run_sql_script(os.path.join('admin', 'sql', 'create_tables.sql'))

    import_data(archive) if archive else print('Skipping data importing.')

    print('Creating primary and foreign keys...')
    run_sql_script(os.path.join('admin', 'sql', 'create_primary_keys.sql'))
    run_sql_script(os.path.join('admin', 'sql', 'create_foreign_keys.sql'))

    print('Creating indexes...')
    run_sql_script(os.path.join('admin', 'sql', 'create_indexes.sql'))

    print("Done!")


@manager.command
def init_test_db():
    """Same as `init_db`, but creates a database that will be used to run tests
    and doesn't import data (no need to do that).
    """
    print('Creating database and user for testing...')
    exit_code = subprocess.call('sudo -u postgres psql < ' +
                                os.path.join('admin', 'sql', 'create_test_db.sql'),
                                shell=True)
    if exit_code != 0:
        raise Exception('Failed to new database and user! Exit code: %i' % exit_code)

    current_app.config['PG_CONNECT'] = current_app.config['PG_CONNECT_TEST']
    run_sql_script(os.path.join('admin', 'sql', 'create_tables.sql'))
    run_sql_script(os.path.join('admin', 'sql', 'create_primary_keys.sql'))
    run_sql_script(os.path.join('admin', 'sql', 'create_foreign_keys.sql'))
    run_sql_script(os.path.join('admin', 'sql', 'create_indexes.sql'))

    print("Done!")


@manager.command
def import_data(archive):
    print('Importing data...')
    import_db_dump(archive)


if __name__ == '__main__':
    manager.run()
