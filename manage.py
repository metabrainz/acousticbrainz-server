from __future__ import print_function

import os
import sys

import click
from brainzutils import cache
from flask import current_app
from flask.cli import FlaskGroup, shell_command

import db
import db.dump
import db.dump_manage
import db.exceptions
import db.stats
import db.user
import webserver
import similarity.manage
import similarity.script

ADMIN_SQL_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'admin', 'sql')

cli = FlaskGroup(add_default_commands=False, create_app=webserver.create_app_flaskgroup)
cli.add_command(shell_command)


@cli.command()
@click.option("--host", "-h", default="0.0.0.0", show_default=True)
@click.option("--port", "-p", default=8080, show_default=True)
def runserver(host, port):
    """Run a development server."""
    reload_on_files = current_app.config['RELOAD_ON_FILES']
    current_app.run(host=host, port=port,
                    extra_files=reload_on_files, threaded=True)


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
        db.dump.import_db_dump(archive)
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
@click.argument("archive", type=click.Path(exists=True))
def import_data(archive):
    """Imports data dump into the database."""

    print('Importing data...')
    db.dump.import_db_dump(archive)


@cli.command()
@click.option('--dummy', '-d', is_flag=True, help="Skip hourly computation, just compute totals")
def compute_stats(dummy=False):
    """Compute outstanding hourly statistics."""
    import datetime
    import pytz
    now = datetime.datetime.now(pytz.utc)
    if dummy:
        db.stats.compute_stats_dummy(now)
    else:
        db.stats.compute_stats(now)


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


# Please keep additional sets of commands down there
cli.add_command(db.dump_manage.cli, name="dump")
cli.add_command(similarity.manage.cli, name="similarity")
cli.add_command(similarity.script.cli, name="script")


if __name__ == '__main__':
    cli()
