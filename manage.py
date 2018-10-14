from __future__ import print_function

import logging
import os
import sys

import click
from brainzutils import cache
from flask import current_app
from flask.cli import FlaskGroup, shell_command
from shutil import copyfile

import db
import db.dump
import db.dump_manage
import db.exceptions
import db.stats
import db.user
import webserver
from db.testing import DatabaseTestCase

ADMIN_SQL_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'admin', 'sql')

cli = FlaskGroup(add_default_commands=False, create_app=webserver.create_app_flaskgroup)
cli.add_command(shell_command)

logging.basicConfig(level=logging.INFO)

@cli.command()
@click.option("--host", "-h", default="0.0.0.0", show_default=True)
@click.option("--port", "-p", default=8080, show_default=True)
def runserver(host, port):
    """Run a development server."""
    reload_on_files = current_app.config['RELOAD_ON_FILES']
    current_app.run(host=host, port=port,
                    extra_files=reload_on_files)


@cli.command()
@click.option("--force", "-f", is_flag=True, help="Drop existing database and user.")
@click.argument("archive", type=click.Path(exists=True), required=False)
@click.option("--skip-create-db", "-s", is_flag=True, help="Skip database creation step.")
def init_db(archive, force, skip_create_db=False):
    """Initialize database and import data.

    This process involves several steps:
    1. Table structure is created.
    2. Data is imported from the archive if it is specified.
    3. Primary keys and foreign keys are created.
    4. Indexes are created.

    Data dump needs to be a .tar.xz archive produced by export command.

    More information about populating a PostgreSQL database efficiently can be
    found at http://www.postgresql.org/docs/current/static/populate.html.
    """

    db.init_db_engine(current_app.config['POSTGRES_ADMIN_URI'])
    if force:
        res = db.run_sql_script_without_transaction(os.path.join(ADMIN_SQL_DIR, 'drop_db.sql'))
        if not res:
            raise Exception('Failed to drop existing database and user! Exit code: %i' % res)

    if not skip_create_db:
        print('Creating user and a database...')
        res = db.run_sql_script_without_transaction(os.path.join(ADMIN_SQL_DIR, 'create_db.sql'))
        if not res:
            raise Exception('Failed to create new database and user! Exit code: %i' % res)

    print('Creating database extensions...')
    db.init_db_engine(current_app.config['POSTGRES_ADMIN_AB_URI'])
    res = db.run_sql_script_without_transaction(os.path.join(ADMIN_SQL_DIR, 'create_extensions.sql'))

    db.init_db_engine(current_app.config['SQLALCHEMY_DATABASE_URI'])

    print('Creating types...')
    db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'create_types.sql'))

    print('Creating tables...')
    db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'create_tables.sql'))

    if archive:
        print('Importing data...')
        db.dump.import_dump(archive)
    else:
        print('Skipping data importing.')
        print('Loading fixtures...')
        print('Models...')
        db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'create_models.sql'))

    print('Creating primary and foreign keys...')
    db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'create_primary_keys.sql'))
    db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'create_foreign_keys.sql'))

    print('Creating indexes...')
    db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'create_indexes.sql'))

    print("Done!")


@cli.command()
@click.option("--drop-constraints", "-d", is_flag=True, help="Drop primary and foreign keys before importing.")
@click.argument("archive", type=click.Path(exists=True))
def import_data(archive, drop_constraints=False):
    """Imports data dump into the database."""
    if drop_constraints:
        print('Dropping primary key and foreign key constraints...')
        db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'drop_foreign_keys.sql'))
        db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'drop_primary_keys.sql'))

    print('Importing data...')
    db.dump.import_db_dump(archive)
    print('Done!')

    if drop_constraints:
        print('Creating primary key and foreign key constraints...')
        db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'create_primary_keys.sql'))
        db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'create_foreign_keys.sql'))


@cli.command()
@click.option("--drop-constraints", "-d", is_flag=True, help="Drop primary and foreign keys before importing.")
@click.argument("archive", type=click.Path(exists=True))
def import_dataset_data(archive, drop_constraints=False):
    """Imports dataset dump into the database."""

    if drop_constraints:
        print('Dropping primary key and foreign key constraints...')
        db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'drop_foreign_keys.sql'))
        db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'drop_primary_keys.sql'))

    print('Importing dataset data...')
    db.dump.import_datasets_dump(archive)
    print('Done!')

    if drop_constraints:
        print('Creating primary key and foreign key constraints...')
        db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'create_primary_keys.sql'))
        db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'create_foreign_keys.sql'))


@cli.command()
def compute_stats():
    """Compute outstanding hourly statistics."""
    import datetime
    import pytz
    db.stats.compute_stats(datetime.datetime.now(pytz.utc))


@cli.command()
def cache_stats():
    """Compute recent stats and add to cache."""
    db.stats.add_stats_to_cache()


@cli.command()
def clear_cache():
    """Clear the cache."""
    cache.flush_all()


@cli.command()
@click.argument("username")
@click.option("--force", "-f", is_flag=True, help="Create user if doesn't exist.")
def add_admin(username, force=False):
    """Make user an admin."""
    try:
        db.user.set_admin(username, admin=True, force=force)
        click.echo("Made %s an admin." % username)
    except db.exceptions.DatabaseException as e:
        click.echo("Error: %s" % e, err=True)
        sys.exit(1)


@cli.command()
@click.argument("username")
def remove_admin(username):
    """Remove admin privileges from a user."""
    try:
        db.user.set_admin(username, admin=False)
        click.echo("Removed admin privileges from %s." % username)
    except db.exceptions.DatabaseException as e:
        click.echo("Error: %s" % e, err=True)
        sys.exit(1)

@cli.command()
def update_sequences():
    print('Updating database sequences...')
    db.dump.update_sequences()
    print('Done!')


@cli.command()
def toggle_site_status():
    """ Bring the site down if it is up, bring it up if down.

    Note: We use nginx configs to set AB up/down status. If the file `is_down.html`
    exists, then it is rendered by default for all pages. Create the file to bring AB down,
    remove it to bring it up.
    """
    if os.path.exists('is_down.html'):
        print('Removing is_down.html...')
        os.remove('is_down.html')
        print('Done!')
    else:
        print('Creating is_down.html from is_down.html.sample')
        copyfile('is_down.html.sample', 'is_down.html')
        print('Done!')


# Please keep additional sets of commands down there
cli.add_command(db.dump_manage.cli, name="dump")


if __name__ == '__main__':
    cli()
