from __future__ import print_function
from flask_script import Manager
from acousticbrainz.data.dump import dump_db, dump_lowlevel_json, dump_highlevel_json, list_incremental_dumps
import shutil
import re
import os

manager = Manager()


@manager.command
def full(location=os.path.join(os.getcwd(), 'export'), threads=None, rotate=False):
    print("Creating full database dump...")
    path = dump_db(location, threads)
    print("Done! Created:", path)

    if rotate:
        print("Removing old dumps (except two latest)...")
        remove_old_archives(location, "acousticbrainzdump-[0-9]+-[0-9]+.tar.xz",
                            is_dir=False, sort_key=lambda x: os.path.getmtime(x))


@manager.command
def incremental(location=os.path.join(os.getcwd(), 'export'), threads=None, inc_id=None):
    print("Creating incremental database dump...")
    inc_id = int(inc_id) if inc_id else None  # converting to proper type
    path = dump_db(location, threads, incremental=True, dump_id=inc_id)
    print("Done! Created:", path)


@manager.option('-nh', '--no-highlevel', dest='no_highlevel', action='store_true',
                help="Don't dump high level data.", default=False)
@manager.option('-nl', '--no-lowlevel', dest='no_lowlevel', action='store_true',
                help="Don't tump low level data.", default=False)
def json(no_highlevel, no_lowlevel):
    if no_highlevel and no_lowlevel:
        print("wut? check your options, mate!")

    if not no_highlevel:
        highlevel_json()

    if not no_lowlevel:
        lowlevel_json()


@manager.command
def lowlevel_json(location=os.path.join(os.getcwd(), 'export'), rotate=False):
    print("Creating low level JSON data dump...")
    path = dump_lowlevel_json(location)
    print("Done! Created:", path)

    if rotate:
        print("Removing old dumps (except two latest)...")
        remove_old_archives(location, "acousticbrainz-lowlevel-json-[0-9]+.tar.bz2",
                            is_dir=False, sort_key=lambda x: os.path.getmtime(x))


@manager.command
def lowlevel_json_incremental(location=os.path.join(os.getcwd(), 'export'), inc_id=None):
    print("Creating incremental low level JSON data dump...")
    inc_id = int(inc_id) if inc_id else None  # converting to proper type
    path = dump_lowlevel_json(location, incremental=True, dump_id=inc_id)
    print("Done! Created:", path)


@manager.command
def highlevel_json(location=os.path.join(os.getcwd(), 'export'), rotate=False):
    print("Creating high level JSON data dump...")
    path = dump_highlevel_json(location)
    print("Done! Created:", path)

    if rotate:
        print("Removing old dumps (except two latest)...")
        remove_old_archives(location, "acousticbrainz-highlevel-json-[0-9]+.tar.bz2",
                            is_dir=False, sort_key=lambda x: os.path.getmtime(x))


@manager.command
def highlevel_json_incremental(location=os.path.join(os.getcwd(), 'export'), inc_id=None):
    print("Creating incremental high level JSON data dump...")
    inc_id = int(inc_id) if inc_id else None  # converting to proper type
    path = dump_highlevel_json(location, incremental=True, dump_id=inc_id)
    print("Done! Created:", path)


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
    entries = filter(lambda x: pattern.search(x), entries)

    if is_dir:
        entries = filter(os.path.isdir, entries)
    else:
        entries = filter(os.path.isfile, entries)

    if sort_key is None:
        entries.sort()
    else:
        entries.sort(key=sort_key)

    # Leaving only two last entries
    for entry in entries[:(-2)]:
        print(' - %s' % entry)
        if is_dir:
            shutil.rmtree(entry)
        else:
            os.remove(entry)


if __name__ == '__main__':
    manager.run()
