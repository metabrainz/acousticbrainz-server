from flask import current_app
from flask.cli import FlaskGroup
from db import dump
import shutil
import click
import re
import os
import webserver
from six.moves import filter


cli = FlaskGroup(add_default_commands=False, create_app=webserver.create_app)


@cli.command(name='full')
@click.option("--location", "-l", default=os.path.join(os.getcwd(), 'export'), show_default=True,
              help="Directory where dumps need to be created")
@click.option("--threads", "-t", type=int)
@click.option("--rotate", "-r", is_flag=True)
@click.pass_context
def full(ctx, location, threads, rotate):
    """This command creates:
    1. New incremental dump record (+ incremental dumps unless it's the first record)
    2. Full database dump
    3. Full JSON dump

    Archive rotation is enabled by default for full dumps.
    """
    dump_id, _, _, _ = dump.prepare_dump(full=True)
    ctx.invoke(full_db, location=location, threads=threads, rotate=rotate, dump_id=dump_id)
    ctx.invoke(json, location=location, rotate=rotate, dump_id=dump_id)


@cli.command(name='full_db')
@click.option("--location", "-l", default=os.path.join(os.getcwd(), 'export'), show_default=True,
              help="Directory where dumps need to be created")
@click.option("--threads", "-t", type=int)
@click.option("--rotate", "-r", is_flag=True)
@click.option("--dump-id", "-id", type=int)
def full_db(location, threads, rotate, dump_id):
    current_app.logger.info("Creating full database dump...")
    if dump_id:
        dump_info = dump.get_dump_info(dump_id)
        if dump_info["dump_type"] != "full":
            raise Exception("Dump ID: %d does not correspond to a full dump!" % dump_id)

    path = dump.dump_public_tables(location, threads, full=True, dump_id=dump_id)
    current_app.logger.info("Done! Created: %s", path)

    if rotate:
        current_app.logger.info("Removing old dumps (except two latest)...")
        remove_old_archives(location, "acousticbrainz-dump-full-[0-9]+-[0-9]+.tar.xz",
                            is_dir=False, sort_key=lambda x: os.path.getmtime(x))


@cli.command()
@click.option("--location", "-l", default=os.path.join(os.getcwd(), 'export'), show_default=True,
              help="Directory where dumps need to be created")
@click.option("--feature-type", "-t", help="Feature type")
def features(location, feature_type):
    """Generate a CSV dump of select low-level features"""
    current_app.logger.info("Creating low-level CSV feature dump...")
    path = dump.dump_lowlevel_features(location, feature_type)
    current_app.logger.info("Done! Created: %s", path)


@cli.command()
@click.option("--location", "-l", default=os.path.join(os.getcwd(), 'export'), show_default=True,
              help="Directory where dumps need to be created")
@click.option("--rotate", "-r", is_flag=True)
@click.option("--no-lowlevel", "-nl", is_flag=True, help="Don't dump low-level data.")
@click.option("--no-highlevel", "-nh", is_flag=True, help="Don't dump high-level data.")
@click.option("--threads", "-t", type=int, default=1, help="Number of threads to use for compression (default=1)")
@click.option("--sample", "-s", is_flag=True, default=False, help="Generate a very small sample dataset")
@click.option("--files-per-archive", type=float, default=float("inf"), help="Split dump into files with this many items each")
def json(location, rotate, no_lowlevel, no_highlevel, threads, sample, files_per_archive):
    if no_lowlevel and no_highlevel:
        current_app.logger.info("wut? check your options, mate!")
        return

    if not no_lowlevel:
        _json_lowlevel(location, rotate, threads, sample, files_per_archive)

    if not no_highlevel:
        _json_highlevel(location, rotate, threads, sample, files_per_archive)


def _json_lowlevel(location, rotate, threads, sample, files_per_archive):
    current_app.logger.info("Creating low-level JSON data dump...")
    path = dump.dump_lowlevel_json(location, threads, sample, num_files_per_archive=files_per_archive)
    current_app.logger.info("Done! Created: %s", path)

    if rotate:
        current_app.logger.info("Removing old dumps (except two latest)...")
        remove_old_archives(location, "acousticbrainz-lowlevel-json-[0-9]+.tar.zst",
                            is_dir=False, sort_key=lambda x: os.path.getmtime(x))


def _json_highlevel(location, rotate, threads, sample, files_per_archive):
    current_app.logger.info("Creating high-level JSON data dump...")
    path = dump.dump_highlevel_json(location, threads, sample, num_files_per_archive=files_per_archive)
    current_app.logger.info("Done! Created: %s", path)

    if rotate:
        current_app.logger.info("Removing old dumps (except two latest)...")
        remove_old_archives(location, "acousticbrainz-highlevel-json-[0-9]+.tar.zst",
                            is_dir=False, sort_key=lambda x: os.path.getmtime(x))


@cli.command(name='incremental')
@click.option("--location", "-l", default=os.path.join(os.getcwd(), 'export'), show_default=True,
              help="Directory where dumps need to be created")
@click.option("--id", type=int)
@click.option("--threads", "-t", type=int)
def incremental(location, id, threads):
    dump_id, start_t, end_t, _ = dump.prepare_dump(dump_id=int(id) if id else None)
    current_app.logger.info("Creating dumps with data between %s and %s:\n" % (start_t, end_t))
    _incremental_db(location, dump_id, threads)
    _incremental_json_lowlevel(location, dump_id)
    _incremental_json_highlevel(location, dump_id)


def _incremental_db(location, dump_id, threads):
    current_app.logger.info("Creating incremental database dump...")
    path = dump.dump_db(location, threads, full=False, dump_id=dump_id)
    current_app.logger.info("Done! Created: %s\n" % path)


def _incremental_json_lowlevel(location, dump_id):
    current_app.logger.info("Creating incremental low-level JSON data dump...")
    path = dump.dump_lowlevel_json(location, full=False, dump_id=dump_id)
    current_app.logger.info("Done! Created: %s\n" % path)


def _incremental_json_highlevel(location, dump_id):
    current_app.logger.info("Creating incremental high-level JSON data dump...")
    path = dump.dump_highlevel_json(location, full=False, dump_id=dump_id)
    current_app.logger.info("Done! Created: %s\n" % path)


@cli.command(name='incremental_info')
@click.option("--all", "-a", is_flag=True, help="Print info about all incremental dumps.")
def incremental_info(all=False):
    """Prints information about incremental dumps: id, timestamp.

    By default outputs information for the latest dump.
    """
    current_app.logger.info("Incremental dumps are disabled")
    return
    info = dump.list_incremental_dumps()
    if info:
        if all:
            current_app.logger.info('Incremental dumps:')
            for current in info:
                current_app.logger.info(' - %s at %s' % current)
        else:
            current_app.logger.info('Last dump ID: %s\nTimestamp: %s' % info[0])
    else:
        current_app.logger.info('No incremental dumps yet.')


def remove_old_archives(location, pattern, is_dir=False, sort_key=None):
    """Removes all files or directories that match specified pattern except two
    last based on sort key.

    Args:
        location: Location that needs to be cleaned up.
        pattern: Regular expression that will be used to filter entries in the
            specified location.
        is_dir: True if directories need to be removed, False if files.
        sort_key: See https://docs.python.org/2/howto/sorting.html?highlight=sort#key-functions.
    """
    entries = [os.path.join(location, e) for e in os.listdir(location)]
    pattern = re.compile(pattern)
    entries = [x for x in entries if pattern.search(x)]

    if is_dir:
        entries = list(filter(os.path.isdir, entries))
    else:
        entries = list(filter(os.path.isfile, entries))

    if sort_key is None:
        entries.sort()
    else:
        entries.sort(key=sort_key)

    # Leaving only two last entries
    for entry in entries[:(-2)]:
        current_app.logger.info(' - %s' % entry)
        if is_dir:
            shutil.rmtree(entry)
        else:
            os.remove(entry)


@cli.command(name='full_dataset_dump')
@click.option("--location", "-l", default=os.path.join(os.getcwd(), 'export'), show_default=True,
              help="Directory where dumps need to be created")
@click.option("--threads", "-t", type=int)
def full_dataset_dump(location, threads):
    current_app.logger.info("Creating full datasets dump...")
    path = dump.dump_dataset_tables(location, threads)
    current_app.logger.info("Done! Created: %s", path)
