from __future__ import print_function
from flask_script import Manager
from acousticbrainz.data.dump_manager import manager as dump_manager
from acousticbrainz.data.dump import import_db_dump
from acousticbrainz.data import run_sql_script
from acousticbrainz import create_app
import os

manager = Manager(create_app)

manager.add_command('dump', dump_manager)


@manager.command
def init_db(archive=None):
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
    print('Creating tables...')
    run_sql_script(os.path.join('admin', 'sql', 'create_tables.sql'))

    if archive:
        print('Importing data...')
        import_db_dump(archive)

    print('Creating primary and foreign keys...')
    run_sql_script(os.path.join('admin', 'sql', 'create_primary_keys.sql'))
    run_sql_script(os.path.join('admin', 'sql', 'create_foreign_keys.sql'))

    print('Creating indexes...')
    run_sql_script(os.path.join('admin', 'sql', 'create_indexes.sql'))

    print("Done!")


if __name__ == '__main__':
    manager.run()
