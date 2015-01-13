"""
Functions for exporting and importing AcousticBrainz data in various formats.

There are two types of data dumps:
1. Full dumps (high/low level information about all tracks in JSON format
or raw information from all tables in TSV format).
2. Incremental dumps (similar to the first one, but some dumped tables don't
include information from the previous dumps).
"""
from __future__ import print_function
from acousticbrainz import config
from admin.utils import create_path
from datetime import datetime
import acousticbrainz
import subprocess
import tempfile
import psycopg2
import tarfile
import shutil
import os

DUMP_CHUNK_SIZE = 1000

# Importing of old dumps will fail if you change
# definition of columns below.
_TABLES = {
    'lowlevel': (
        'id',
        'mbid',
        'build_sha1',
        'lossless',
        'data',
        'submitted',
        'data_sha256',
    ),
    'highlevel': (
        'id',
        'mbid',
        'build_sha1',
        'data',
        'submitted',
    ),
    'highlevel_json': (
        'id',
        'data',
        'data_sha256',
    ),
    'statistics': (
        'name',
        'value',
        'collected',
    ),
    'incremental_dumps': (
        'id',
        'created',
    ),
}


def dump_db(location, threads=None, incremental=False):
    """Create complete database dump in a specified location.

    Args:
        location: Directory where archive will be created.
        threads: Maximal number of threads to run during compression.
        incremental: False if resulting data dump should be complete, False if
            it needs to be incremental.

    Returns:
        Path to created dump.
    """
    create_path(location)
    time_now = datetime.today()

    if incremental:
        last = get_inc_dump_info()
        start_t = last[1] if last else None
        dump_id, end_t = _create_new_inc_dump_record()
        archive_name = 'acousticbrainzdump-incr-%s.tar.xz' % dump_id
    else:
        start_t, end_t = None, None
        archive_name = 'acousticbrainzdump-%s.tar.xz' % time_now.strftime('%Y%m%d-%H%M%S')

    archive_path = os.path.join(location, archive_name)
    with open(archive_path, 'w') as archive:

        pxz_command = ['pxz', '--compress']
        if threads is not None:
            pxz_command.append('-T %s' % threads)
        pxz = subprocess.Popen(pxz_command, stdin=subprocess.PIPE, stdout=archive)

        # Creating the archive
        with tarfile.open(fileobj=pxz.stdin, mode='w|') as tar:
            # TODO(roman): Get rid of temporary directories and write directly to tar file
            temp_dir = tempfile.mkdtemp()

            # Adding metadata
            schema_seq_path = os.path.join(temp_dir, 'SCHEMA_SEQUENCE')
            with open(schema_seq_path, 'w') as f:
                f.write(str(acousticbrainz.__version__))
            tar.add(schema_seq_path, arcname='SCHEMA_SEQUENCE')
            timestamp_path = os.path.join(temp_dir, 'TIMESTAMP')
            with open(timestamp_path, 'w') as f:
                f.write(time_now.isoformat(' '))
            tar.add(timestamp_path, arcname='TIMESTAMP')
            tar.add(os.path.join('licenses', 'COPYING-PublicDomain'), arcname='COPYING')

            archive_tables_dir = os.path.join(temp_dir, 'abdump', 'abdump')
            create_path(archive_tables_dir)
            _copy_tables(archive_tables_dir, start_t, end_t)
            tar.add(archive_tables_dir, arcname='abdump')

            shutil.rmtree(temp_dir)  # Cleanup

        pxz.stdin.close()

    return archive_path


def _copy_tables(location, start_time=None, end_time=None):
    """Copies all tables into separate files within a specified directory.

    You can also define time frame that will be used during data selection.
    This will only work on tables that support incremental dumping: "lowlevel"
    and "highlevel".
    """
    conn = psycopg2.connect(config.PG_CONNECT)
    cursor = conn.cursor()

    # Copying tables that can be split up for incremental dumps

    if start_time or end_time:
        start_cond = "submitted > '%s'" % str(start_time) if start_time else ''
        end_cond = "submitted <= '%s'" % str(end_time) if end_time else ''
        if start_time and end_time:
            where = "WHERE %s AND %s" % (start_cond, end_cond)
        else:
            where = "WHERE %s%s" % (start_cond, end_cond)
    else:
        where = ''

    # lowlevel
    with open(os.path.join(location, 'lowlevel'), 'w') as f:
        print(" - Copying table lowlevel...")
        cursor.copy_to(f, "(SELECT %s FROM lowlevel %s)" %
                       (', '.join(_TABLES['lowlevel']), where))

    # highlevel
    with open(os.path.join(location, 'highlevel'), 'w') as f:
        print(" - Copying table highlevel...")
        where = "WHERE submitted >= '%s'" % str(start_time) if start_time else ''
        cursor.copy_to(f, "(SELECT %s FROM highlevel %s)" %
                       (', '.join(_TABLES['highlevel']), where))

    # Copying tables that are always dumped with all rows
    for table in _TABLES.keys():
        if table in ('lowlevel', 'highlevel',):
            continue
        print(" - Copying table %s..." % table)
        with open(os.path.join(location, table), 'w') as f:
            cursor.copy_to(f, table, columns=_TABLES[table])


def import_db_dump(archive_path):
    """Import data from .tar.xz archive into the database."""
    pxz_command = ['pxz', '--decompress', '--stdout', archive_path]
    pxz = subprocess.Popen(pxz_command, stdout=subprocess.PIPE)

    table_names = _TABLES.keys()

    conn = psycopg2.connect(config.PG_CONNECT)
    cursor = conn.cursor()

    with tarfile.open(fileobj=pxz.stdout, mode='r|') as tar:
        for member in tar:

            if member.name == 'SCHEMA_SEQUENCE':
                # Verifying schema version
                schema_seq = int(tar.extractfile(member).read().strip())
                if schema_seq != acousticbrainz.__version__:
                    raise Exception("Incorrect schema version! Expected: %d, got: %d."
                                    "Please, get the latest version of the dump."
                                    % (acousticbrainz.__version__, schema_seq))
                else:
                    print("Schema version verified.")

            else:
                file_name = member.name.split('/')[-1]
                if file_name in table_names:
                    print(" - Importing data into %s table..." % file_name)
                    cursor.copy_from(tar.extractfile(member), '"%s"' % file_name,
                                     columns=_TABLES[file_name])

    conn.commit()
    pxz.stdout.close()


def dump_lowlevel_json(location):
    """Create JSON dumps with all low level documents.

    Args:
        location: Directory where archive will be created.

    Returns:
        Path to created low level JSON dump.
    """
    conn = psycopg2.connect(config.PG_CONNECT)
    cur = conn.cursor()
    cur2 = conn.cursor()

    create_path(location)
    archive_path = os.path.join(location, "acousticbrainz-lowlevel-json-%s-json.tar.bz2" %
                                datetime.today().strftime('%Y%m%d'))

    with tarfile.open(archive_path, "w:bz2") as tar:
        last_mbid = None
        index = 0
        cur.execute("SELECT id FROM lowlevel ll ORDER BY mbid")
        while True:
            id_list = cur.fetchmany(size=DUMP_CHUNK_SIZE)
            if not id_list:
                break

            id_list = tuple([i[0] for i in id_list])

            count = 0
            cur2.execute("SELECT mbid, data::text FROM lowlevel WHERE id IN %s ORDER BY mbid", (id_list,))
            while True:
                row = cur2.fetchone()
                if not row:
                    break

                mbid = row[0]
                json = row[1]

                if count == 0:
                    print(" - %s" % mbid)

                if mbid == last_mbid:
                    index += 1
                else:
                    index = 0

                filename = os.path.join(location, mbid + "-%d.json" % index)
                f = open(filename, "w")
                f.write(json)
                f.close()

                arcname = os.path.join("acousticbrainz-lowlevel-json-" + datetime.today().strftime('%Y%m%d'), "lowlevel", mbid[0:1], mbid[0:2], mbid + "-%d.json" % index)
                tar.add(filename, arcname=arcname)
                os.unlink(filename)

                last_mbid = mbid
                count += 1

        # Copying legal text
        tar.add(os.path.join("licenses", "COPYING-PublicDomain"),
                arcname=os.path.join("acousticbrainz-lowlevel-json-" + datetime.today().strftime('%Y%m%d'),
                                     'COPYING'))

    return archive_path


def dump_highlevel_json(location):
    """Create JSON dumps with all high level documents.

    Args:
        location: Directory where archive will be created.

    Returns:
        Path to created high level JSON dump.
    """
    conn = psycopg2.connect(config.PG_CONNECT)
    cur = conn.cursor()
    cur2 = conn.cursor()

    create_path(location)
    archive_path = os.path.join(location, "acousticbrainz-highlevel-json-%s-json.tar.bz2" %
                                datetime.today().strftime('%Y%m%d'))

    with tarfile.open(archive_path, "w:bz2") as tar:
        last_mbid = None
        index = 0
        cur.execute("SELECT hl.id FROM highlevel hl, highlevel_json hlj WHERE hl.data = hlj.id ORDER BY mbid")
        while True:
            id_list = cur.fetchmany(size=DUMP_CHUNK_SIZE)
            if not id_list:
                break

            id_list = tuple([i[0] for i in id_list])

            count = 0
            cur2.execute("""SELECT mbid, hlj.data::text
                             FROM highlevel hl, highlevel_json hlj
                            WHERE hl.data = hlj.id
                              AND hl.id IN %s
                            ORDER BY mbid""", (id_list, ))
            while True:
                row = cur2.fetchone()
                if not row:
                    break

                mbid = row[0]
                json = row[1]

                if count == 0:
                    print(" - write %s" % mbid)

                if mbid == last_mbid:
                    index += 1
                else:
                    index = 0

                filename = os.path.join(location, mbid + "-%d.json" % index)
                f = open(filename, "w")
                f.write(json)
                f.close()

                arcname = os.path.join("acousticbrainz-highlevel-json-" + datetime.today().strftime('%Y%m%d'), "highlevel", mbid[0:1], mbid[0:2], mbid + "-%d.json" % index)
                tar.add(filename, arcname=arcname)
                os.unlink(filename)

                last_mbid = mbid
                count += 1

        # Copying legal text
        tar.add(os.path.join("licenses", "COPYING-PublicDomain"),
                arcname=os.path.join("acousticbrainz-highlevel-json-" + datetime.today().strftime('%Y%m%d'),
                                     'COPYING'))

    return archive_path


def _create_new_inc_dump_record():
    """Creates new record for incremental dump and returns its ID and creation time."""
    db = psycopg2.connect(config.PG_CONNECT)
    cursor = db.cursor()
    cursor.execute("INSERT INTO incremental_dumps (created) VALUES (now()) RETURNING id, created")
    db.commit()
    return cursor.fetchone()


def get_inc_dump_info(all=False):
    """Returns information about incremental dumps.

    Args:
        all: Whether to return information about all incremental dumps (True)
            or just the last one.

    Returns:
        * One (id, created) pair if all is set to False.
        * List of (id, created) pairs if all is set to True.
        * None if there are no incremental dumps.
    """
    cursor = psycopg2.connect(config.PG_CONNECT).cursor()
    cursor.execute("SELECT id, created FROM incremental_dumps ORDER BY id DESC")
    return cursor.fetchall() if all else cursor.fetchone()
