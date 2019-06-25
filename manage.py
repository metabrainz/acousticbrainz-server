from __future__ import print_function

import logging
import os
import sys

import click
from brainzutils import cache
import flask.cli
from flask import current_app
from flask.cli import FlaskGroup
from shutil import copyfile

import db
import db.data
import db.dump
import db.dump_manage
import db.exceptions
import db.submission_stats
import db.user
import webserver
import similarity.manage
import similarity.script


ADMIN_SQL_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'admin', 'sql')

cli = FlaskGroup(add_default_commands=False, create_app=webserver.create_app_flaskgroup)

logging.basicConfig(level=logging.INFO)


@cli.command(name='runserver')
@click.option('--host', '-h', default='0.0.0.0',
              help='The interface to bind to.')
@click.option('--port', '-p', default=8080,
              help='The port to bind to.')
@click.option('--debugger/--no-debugger', default=None,
              help='Enable or disable the debugger. By default the debugger '
              'is active if debug is enabled.')
@flask.cli.pass_script_info
def runserver(info, host, port, debugger):
    """Run a local development server.
    This server is for development purposes only. It does not provide
    the stability, security, or performance of production WSGI servers.
    The reloader and debugger are enabled by default if
    FLASK_ENV=development or FLASK_DEBUG=1.

    This is a copy of flask.cli.run_command, which passes the additional
    argument `extra_files` to `run_simple`. Some defaults are set that are
    available as options in the original method."""

    debug = flask.helpers.get_debug_flag()
    reload = debug

    if debugger is None:
        debugger = debug

    eager_loading = not reload

    flask.cli.show_server_banner(flask.helpers.get_env(), debug, info.app_import_path, eager_loading)
    app = flask.cli.DispatchingApp(info.load_app, use_eager_loading=eager_loading)
    reload_on_files = info.load_app().config['RELOAD_ON_FILES']

    from werkzeug.serving import run_simple
    run_simple(host, port, app, use_reloader=reload, use_debugger=debugger,
               extra_files=reload_on_files)


@cli.command(name='init_db')
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
    5. Similarity metrics metadata is populated.

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

    print('Creating schema...')
    db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'create_schema.sql'))

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

    print('Populating similarity_metrics table...')
    db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'populate_metrics_table.sql'))

    print("Done!")


@cli.command(name='import_data')
@click.option("--drop-constraints", "-d", is_flag=True, help="Drop primary and foreign keys before importing.")
@click.argument("archive", type=click.Path(exists=True))
def import_data(archive, drop_constraints=False):
    """Imports data dump into the database."""
    if drop_constraints:
        print('Dropping primary key and foreign key constraints...')
        db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'drop_foreign_keys.sql'))
        db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'drop_primary_keys.sql'))

    print('Importing data...')
    db.dump.import_dump(archive)
    print('Done!')

    if drop_constraints:
        print('Creating primary key and foreign key constraints...')
        db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'create_primary_keys.sql'))
        db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'create_foreign_keys.sql'))


@cli.command(name='import_dataset_data')
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


@cli.command(name='compute_stats')
def compute_stats():
    """Compute outstanding hourly statistics."""
    import datetime
    import pytz
    db.submission_stats.compute_stats(datetime.datetime.now(pytz.utc))


@cli.command(name='cache_stats')
def cache_stats():
    """Compute recent stats and add to cache."""
    db.submission_stats.add_stats_to_cache()


@cli.command(name='clear_cache')
def clear_cache():
    """Clear the cache."""
    cache.flush_all()


@cli.command(name='add_admin')
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


@cli.command(name='remove_admin')
@click.argument("username")
def remove_admin(username):
    """Remove admin privileges from a user."""
    try:
        db.user.set_admin(username, admin=False)
        click.echo("Removed admin privileges from %s." % username)
    except db.exceptions.DatabaseException as e:
        click.echo("Error: %s" % e, err=True)
        sys.exit(1)


@cli.command(name='update_sequences')
def update_sequences():
    print('Updating database sequences...')
    db.dump.update_sequences()
    print('Done!')


@cli.command(name='toggle_site_status')
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


@cli.group()
@click.pass_context
def highlevel(ctx):
    """Analyse highlevel results"""
    pass


@highlevel.command(name="list_failed_rows")
@click.option("--verbose", "-v", is_flag=True, help="Lists failed highlevel rows.")
def list_failed_rows(verbose):
    """ Displays the number of rows which do not contain highlevel metadata

    When run with -v, also output rowid, mbid, submission offset of each failed submission
    """

    try:
        rows = db.data.get_failed_highlevel_submissions()
        num_failed_rows = len(rows)
        click.echo("Number of highlevel rows that failed processing: %s" % num_failed_rows)
        if verbose:
            click.echo("rowid,mbid,submission_offset")
            for row in rows:
                click.echo("%s,%s,%s" % (row["id"], row["gid"], row["submission_offset"]))

    except db.exceptions.DatabaseException as e:
        click.echo("Error: %s" % e, err=True)
        sys.exit(1)


@highlevel.command(name="remove_failed_rows")
def remove_failed_rows():
    """ Deletes highlevel rows which do not have highlevel metadata"""
    try:
        click.echo("removing failed highlevel rows...")
        db.data.remove_failed_highlevel_submissions()
        click.echo("done")
    except db.exceptions.DatabaseException as e:
        click.echo("Error: %s" % e, err=True)
        sys.exit(1)


# Keep additional sets of commands down here
cli.add_command(db.dump_manage.cli, name="dump")
cli.add_command(similarity.manage.cli, name="similarity")
cli.add_command(similarity.script.cli, name="similarity-script")

if __name__ == '__main__':
    cli()
