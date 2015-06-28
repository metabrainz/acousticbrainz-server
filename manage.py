from __future__ import print_function
import data
import data.dump
import data.dump_manage
from web_server import create_app
import subprocess
import os
import click

ADMIN_SQL_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'admin', 'sql')

cli = click.Group()


@cli.command()
@click.option("--host", "-h", default="0.0.0.0", show_default=True)
@click.option("--port", "-p", default=8080, show_default=True)
@click.option("--debug", "-d", type=bool,
              help="Turns debugging mode on or off. If specified, overrides "
                   "'DEBUG' value in the config file.")
def runserver(host, port, debug):
    create_app().run(host=host, port=port, debug=debug)


@cli.command()
@click.option("--archive", help="Path to data dump that needs to be imported.")
@click.option("--force", "-f", is_flag=True, help="Drop existing database and user.")
def init_db(archive, force):
    """Initializes database and imports data if needed.

    This process involves several steps:
    1. Table structure is created.
    2. Data is imported from the archive if it is specified.
    3. Primary keys and foreign keys are created.
    4. Indexes are created.

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

    data.init_db_connection(config.PG_CONNECT)

    print('Creating tables...')
    data.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'create_tables.sql'))

    import_data(archive) if archive else print('Skipping data importing.')

    print('Creating primary and foreign keys...')
    data.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'create_primary_keys.sql'))
    data.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'create_foreign_keys.sql'))

    print('Creating indexes...')
    data.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'create_indexes.sql'))

    print("Done!")


@cli.command()
@click.option("--force", "-f", is_flag=True, help="Drop existing database and user.")
def init_test_db(force=False):
    """Same as `init_db` command, but creates a database that will be used to
    run tests and doesn't import data (no need to do that).

    `PG_CONNECT_TEST` variable must be defined in the config file.
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

    data.init_db_connection(config.PG_CONNECT_TEST)

    data.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'create_tables.sql'))
    data.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'create_primary_keys.sql'))
    data.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'create_foreign_keys.sql'))
    data.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'create_indexes.sql'))

    print("Done!")


@cli.command()
@click.argument("archive")
def import_data(archive):
    """Imports data dump into the database."""
    print('Importing data...')
    data.dump.import_db_dump(archive)


cli.add_command(data.dump_manage.cli, name="dump")


if __name__ == '__main__':
    import config
    data.init_db_connection(config.PG_CONNECT)
    cli()
