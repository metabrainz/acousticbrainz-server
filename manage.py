from __future__ import print_function
import db
import db.cache
import db.dump
import db.stats
import db.dump_manage
from webserver import create_app
import subprocess
import os
import click
import config

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


def _run_psql(script, database=None):
    script = os.path.join(ADMIN_SQL_DIR, script)
    command = ['psql', '-p', config.PG_PORT, '-U', config.PG_SUPER_USER, '-f', script]
    if database:
        command.extend(['-d', database])
    exit_code = subprocess.call(command)

    return exit_code

@cli.command()
@click.option("--force", "-f", is_flag=True, help="Drop existing database and user.")
@click.argument("archive", type=click.Path(exists=True), required=False)
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
        exit_code = _run_psql('drop_db.sql')
        if exit_code != 0:
            raise Exception('Failed to drop existing database and user! Exit code: %i' % exit_code)

    print('Creating user and a database...')
    exit_code = _run_psql('create_db.sql')
    if exit_code != 0:
        raise Exception('Failed to create new database and user! Exit code: %i' % exit_code)

    print('Creating database extensions...')
    exit_code = _run_psql('create_extensions.sql', 'acousticbrainz94')
    if exit_code != 0:
        raise Exception('Failed to create database extensions! Exit code: %i' % exit_code)

    db.init_db_engine(config.SQLALCHEMY_DATABASE_URI)

    print('Creating types...')
    db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'create_types.sql'))

    print('Creating tables...')
    db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'create_tables.sql'))

    if archive:
        print('Importing data...')
        db.dump.import_db_dump(archive)
    else:
        print('Skipping data importing.')

    print('Creating primary and foreign keys...')
    db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'create_primary_keys.sql'))
    db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'create_foreign_keys.sql'))

    print('Creating indexes...')
    db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'create_indexes.sql'))

    print("Done!")


@cli.command()
@click.option("--force", "-f", is_flag=True, help="Drop existing database and user.")
def init_test_db(force=False):
    """Same as `init_db` command, but creates a database that will be used to
    run tests and doesn't import data (no need to do that).

    `SQLALCHEMY_TEST_URI` must be defined in the config file.
    """
    if force:
        exit_code = _run_psql('drop_test_db.sql')
        if exit_code != 0:
            raise Exception('Failed to drop existing database and user! Exit code: %i' % exit_code)

    print('Creating database and user for testing...')
    exit_code = _run_psql('create_test_db.sql')
    if exit_code != 0:
        raise Exception('Failed to create new database and user! Exit code: %i' % exit_code)

    exit_code = _run_psql('create_extensions.sql', 'ab_test')
    if exit_code != 0:
        raise Exception('Failed to create database extensions! Exit code: %i' % exit_code)

    db.init_db_engine(config.SQLALCHEMY_TEST_URI)

    db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'create_types.sql'))
    db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'create_tables.sql'))
    db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'create_primary_keys.sql'))
    db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'create_foreign_keys.sql'))
    db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'create_indexes.sql'))

    print("Done!")


@cli.command()
@click.argument("archive", type=click.Path(exists=True))
def import_data(archive):
    """Imports data dump into the database."""
    db.init_db_engine(config.SQLALCHEMY_DATABASE_URI)
    print('Importing data...')
    db.dump.import_db_dump(archive)


cli.add_command(db.dump_manage.cli, name="dump")


@cli.command()
def compute_stats():
    """Compute any outstanding hourly stats and add to the database."""
    db.init_db_engine(config.SQLALCHEMY_DATABASE_URI)
    import datetime
    import pytz
    db.stats.compute_stats(datetime.datetime.now(pytz.utc))


@cli.command()
def cache_stats():
    """Compute recent stats and add to memcache."""
    db.init_db_engine(config.SQLALCHEMY_DATABASE_URI)
    db.cache.init(config.MEMCACHED_SERVERS)
    db.stats.add_stats_to_cache()


if __name__ == '__main__':
    cli()
