#!/usr/bin/env python

import sys
sys.path.append("../acousticbrainz")

import tarfile
import shutil
import errno
import os
import psycopg2
import config
from datetime import datetime
from time import gmtime, strftime

def create_path(path):
    """Creates a directory structure if it doesn't exist yet."""
    try:
        os.makedirs(path)
    except OSError as exception:
        if exception.errno != errno.EEXIST:
            sys.exit("Failed to create directory structure %s. Error: %s" % (path, exception))

def remove_old_archives(location, pattern, is_dir=False, sort_key=None):
    """Removes all files or directories that match specified pattern except two last.

    :param location: Location that needs to be cleaned up.
    :param pattern: Regular expression that will be used to filter entries in the specified location.
    :param is_dir: True if directories need to be removed, False if files.
    :param sort_key: See https://docs.python.org/2/howto/sorting.html?highlight=sort#key-functions.
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

def dump_json(location=os.path.join(os.getcwd(), 'dump'), rotate=False):
    """
        Create JSON dumps with all low and high level documents
    """

    temp_dir = '%s/temp' % location
    create_path(temp_dir)

    conn = psycopg2.connect(config.PG_CONNECT)
    cur = conn.cursor()

    with tarfile.open("%s/acousticbrainz-%s-json.tar.bz2" % (location, datetime.today().strftime('%Y%m%d')), "w:bz2") as tar:
        cur.execute("""SELECT mbid, data::text FROM lowlevel ll""")
        for row in cur.fetchone():
            mbid = row[0]
            json = row[1]

            # Creating directory structure for the documents
            path = os.path.join(location, mbid[0:1], mbid[0:2])
            create_path(path)

            f = open(os.path.join(path, mbid + "-lowlevel.json"), 'w')
            f.write(ll_json)
            f.close()

            f = open(os.path.join(path, mbid + "-highlevel.json"), 'w')
            f.write(hl_json)
            f.close()

        tar.add(path, arcname='data')

        # Copying legal text
        tar.add("licenses/CC0.txt", arcname='COPYING')

        print(" + %s" % mbid)

    shutil.rmtree(temp_dir)  # Cleanup

    if rotate:
        print("Removing old sets of archives (except two latest)...")
        remove_old_archives(location, "acousticbrainz-[0-9]+-json.tar.bz2",
                            is_dir=False, sort_key=lambda x: os.path.getmtime(x))

    print("Done!")

if __name__ == "__main__":
    dump_json()
