from __future__ import print_function
from flask_script import Manager
import os
import acousticbrainz
from acousticbrainz.data import run_sql_script
from acousticbrainz.data.dump import dump_db, import_db_dump, dump_lowlevel_json, dump_highlevel_json, list_incremental_dumps
from admin.utils import remove_old_archives

app = acousticbrainz.create_app()
manager = Manager(app)


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


@manager.command
def export(location=os.path.join(os.getcwd(), 'export'), threads=None, rotate=False):
    print("Creating full database dump...")
    path = dump_db(location, threads)
    print("Done! Created:", path)

    if rotate:
        print("Removing old dumps (except two latest)...")
        remove_old_archives(location, "acousticbrainzdump-[0-9]+-[0-9]+.tar.xz",
                            is_dir=False, sort_key=lambda x: os.path.getmtime(x))


@manager.command
def export_incremental(location=os.path.join(os.getcwd(), 'export'), threads=None, inc_id=None):
    print("Creating incremental database dump...")
    inc_id = int(inc_id) if inc_id else None  # converting to proper type
    path = dump_db(location, threads, incremental=True, dump_id=inc_id)
    print("Done! Created:", path)


@manager.option('-nh', '--no-highlevel', dest='no_highlevel', action='store_true',
                help="Don't dump high level data.", default=False)
@manager.option('-nl', '--no-lowlevel', dest='no_lowlevel', action='store_true',
                help="Don't tump low level data.", default=False)
def export_json(no_highlevel, no_lowlevel):
    if no_highlevel and no_lowlevel:
        print("wut? check your options, mate!")

    if not no_highlevel:
        export_highlevel_json()

    if not no_lowlevel:
        export_lowlevel_json()


@manager.command
def export_lowlevel_json(location=os.path.join(os.getcwd(), 'export'), rotate=False):
    print("Creating lowlevel JSON data dump...")
    path = dump_lowlevel_json(location)
    print("Done! Created:", path)

    if rotate:
        print("Removing old dumps (except two latest)...")
        remove_old_archives(location, "acousticbrainz-lowlevel-json-[0-9]+-json.tar.bz2",
                            is_dir=False, sort_key=lambda x: os.path.getmtime(x))


@manager.command
def export_lowlevel_json_incremental(location=os.path.join(os.getcwd(), 'export'), inc_id=None):
    print("Creating incremental lowlevel JSON data dump...")
    inc_id = int(inc_id) if inc_id else None  # converting to proper type
    path = dump_lowlevel_json(location, incremental=True, dump_id=inc_id)
    print("Done! Created:", path)


@manager.command
def export_highlevel_json(location=os.path.join(os.getcwd(), 'export'), rotate=False):
    print("Creating highlevel JSON data dump...")
    path = dump_highlevel_json(location)
    print("Done! Created:", path)

    if rotate:
        print("Removing old dumps (except two latest)...")
        remove_old_archives(location, "acousticbrainz-highlevel-json-[0-9]+-json.tar.bz2",
                            is_dir=False, sort_key=lambda x: os.path.getmtime(x))


@manager.command
def get_incremental_info(all=False):
    info = list_incremental_dumps()
    if info:
        if all:
            print('Incremental dumps:')
            for current in info:
                print(' - %s at %s' % current)
        else:
            print('Last dump ID: %s\nTimestamp: %s' % info[0])
    else:
        print('No incremental dumps yet.')


if __name__ == '__main__':
    manager.run()
