from __future__ import print_function
from flask_script import Manager
from acousticbrainz.data.dump import dump_db, dump_lowlevel_json, \
    dump_highlevel_json, prepare_incremental_dump, list_incremental_dumps
import shutil
import re
import os

manager = Manager()


@manager.command
def full_db(location=os.path.join(os.getcwd(), 'export'), threads=None, rotate=False):
    print("Creating full database dump...")
    path = dump_db(location, threads)
    print("Done! Created:", path)

    if rotate:
        print("Removing old dumps (except two latest)...")
        remove_old_archives(location, "acousticbrainz-dump-[0-9]+-[0-9]+.tar.xz",
                            is_dir=False, sort_key=lambda x: os.path.getmtime(x))


@manager.option('-l', '--location', dest='location', action='store_true',
                default=os.path.join(os.getcwd(), 'export'),
                help="Directory where dumps need to be created")
@manager.option('-r', '--rotate', dest='rotate', action='store_true', default=False)
@manager.option('-nl', '--no-lowlevel', dest='no_lowlevel', action='store_true',
                default=False, help="Don't tump low level data.")
@manager.option('-nh', '--no-highlevel', dest='no_highlevel', action='store_true',
                default=False, help="Don't dump high level data.")
def json(location, rotate, no_lowlevel, no_highlevel):
    if no_lowlevel and no_highlevel:
        print("wut? check your options, mate!")

    if not no_lowlevel:
        _json_lowlevel(location, rotate)

    if not no_highlevel:
        _json_highlevel(location, rotate)


def _json_lowlevel(location, rotate):
    print("Creating low level JSON data dump...")
    path = dump_lowlevel_json(location)
    print("Done! Created: %s\n" % path)

    if rotate:
        print("Removing old dumps (except two latest)...")
        remove_old_archives(location, "acousticbrainz-lowlevel-json-[0-9]+.tar.bz2",
                            is_dir=False, sort_key=lambda x: os.path.getmtime(x))


def _json_highlevel(location, rotate):
    print("Creating high level JSON data dump...")
    path = dump_highlevel_json(location)
    print("Done! Created: %s\n" % path)

    if rotate:
        print("Removing old dumps (except two latest)...")
        remove_old_archives(location, "acousticbrainz-highlevel-json-[0-9]+.tar.bz2",
                            is_dir=False, sort_key=lambda x: os.path.getmtime(x))


@manager.command
def incremental(location=os.path.join(os.getcwd(), 'export'), id=None, threads=None):
    dump_id, start_t, end_t = prepare_incremental_dump(int(id) if id else None)
    print("Creating incremental dumps with data between %s and %s:\n" % (start_t, end_t))
    _incremental_db(location, dump_id, threads)
    _incremental_json_lowlevel(location, dump_id)
    _incremental_json_highlevel(location, dump_id)


def _incremental_db(location, id, threads):
    print("Creating incremental database dump...")
    path = dump_db(location, threads, incremental=True, dump_id=id)
    print("Done! Created: %s\n" % path)


def _incremental_json_lowlevel(location, id):
    print("Creating incremental low level JSON data dump...")
    path = dump_lowlevel_json(location, incremental=True, dump_id=id)
    print("Done! Created: %s\n" % path)


def _incremental_json_highlevel(location, id):
    print("Creating incremental high level JSON data dump...")
    path = dump_highlevel_json(location, incremental=True, dump_id=id)
    print("Done! Created: %s\n" % path)


@manager.command
def incremental_info(all=False):
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
