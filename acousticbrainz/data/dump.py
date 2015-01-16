"""
Functions for exporting and importing AcousticBrainz data in various formats.

There are two types of data dumps:
1. Full dumps (high/low level information about all tracks in JSON format
or raw information from all tables in TSV format).
2. Incremental dumps (similar to the first one, but some dumped tables don't
include information from the previous dumps).
"""
from __future__ import print_function
from collections import defaultdict
from admin.utils import create_path
from flask import current_app
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


def dump_db(location, threads=None, incremental=False, dump_id=None):
    """Create database dump in a specified location.

    Args:
        location: Directory where archive will be created.
        threads: Maximal number of threads to run during compression.
        incremental: False if resulting data dump should be complete, False if
            it needs to be incremental.
        dump_id: If you need to reproduce previously created incremental dump,
            its identifier (integer) can be specified there.

    Returns:
        Path to created dump.
    """
    create_path(location)
    time_now = datetime.today()

    if incremental:
        dump_id, start_t, end_t = _prepare_incremental_dump(dump_id)
        archive_name = 'acousticbrainz-dump-incr-%s' % dump_id
    else:
        start_t, end_t = None, None  # full
        archive_name = 'acousticbrainz-dump-%s' % time_now.strftime('%Y%m%d-%H%M%S')

    archive_path = os.path.join(location, archive_name + '.tar.xz')
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
            tar.add(schema_seq_path,
                    arcname=os.path.join(archive_name, 'SCHEMA_SEQUENCE'))
            timestamp_path = os.path.join(temp_dir, 'TIMESTAMP')
            with open(timestamp_path, 'w') as f:
                f.write(time_now.isoformat(' '))
            tar.add(timestamp_path,
                    arcname=os.path.join(archive_name, 'TIMESTAMP'))
            tar.add(os.path.join('licenses', 'COPYING-PublicDomain'),
                    arcname=os.path.join(archive_name, 'COPYING'))

            archive_tables_dir = os.path.join(temp_dir, 'abdump', 'abdump')
            create_path(archive_tables_dir)
            _copy_tables(archive_tables_dir, start_t, end_t)
            tar.add(archive_tables_dir, arcname=os.path.join(archive_name, 'abdump'))

            shutil.rmtree(temp_dir)  # Cleanup

        pxz.stdin.close()

    return archive_path


def _copy_tables(location, start_time=None, end_time=None):
    """Copies all tables into separate files within a specified directory.

    You can also define time frame that will be used during data selection.
    This will only work on tables that support incremental dumping: "lowlevel"
    and "highlevel".
    """
    conn = psycopg2.connect(current_app.config["PG_CONNECT"])
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
        cursor.copy_to(f, "(SELECT %s FROM highlevel %s)" %
                       (', '.join(_TABLES['highlevel']), where))

    # highlevel_json
    with open(os.path.join(location, 'highlevel_json'), 'w') as f:
        print(" - Copying table highlevel_json...")
        query = """SELECT %s FROM highlevel_json WHERE id IN (
                       SELECT data FROM highlevel %s
                )""" % (', '.join(_TABLES['highlevel_json']), where)
        cursor.copy_to(f, "(%s)" % query)

    # Copying tables that are always dumped with all rows
    for table in _TABLES.keys():
        if table in ('lowlevel', 'highlevel', 'highlevel_json'):
            continue
        print(" - Copying table %s..." % table)
        with open(os.path.join(location, table), 'w') as f:
            cursor.copy_to(f, table, columns=_TABLES[table])


def import_db_dump(archive_path):
    """Import data from .tar.xz archive into the database."""
    pxz_command = ['pxz', '--decompress', '--stdout', archive_path]
    pxz = subprocess.Popen(pxz_command, stdout=subprocess.PIPE)

    table_names = _TABLES.keys()

    conn = psycopg2.connect(current_app.config["PG_CONNECT"])
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


def dump_lowlevel_json(location, incremental=False, dump_id=None):
    """Create JSON dump with low level data.

    Args:
        location: Directory where archive will be created.
        incremental: False if resulting JSON dump should be complete, False if
            it needs to be incremental.
        dump_id: If you need to reproduce previously created incremental dump,
            its identifier (integer) can be specified there.

    Returns:
        Path to created low level JSON dump.
    """
    create_path(location)

    if incremental:
        dump_id, start_time, end_time = _prepare_incremental_dump(dump_id)
        archive_name = 'acousticbrainz-lowlevel-json-incr-%s' % dump_id
    else:
        start_time, end_time = None, None  # full
        archive_name = 'acousticbrainz-lowlevel-json-%s' % \
                       datetime.today().strftime('%Y%m%d')

    archive_path = os.path.join(location, archive_name + '.tar.bz2')
    with tarfile.open(archive_path, "w:bz2") as tar:
        db = psycopg2.connect(current_app.config["PG_CONNECT"])
        cursor = db.cursor()

        mbid_occurences = defaultdict(int)

        # Need to count how many duplicate MBIDs are there before start_time
        if start_time:
            cursor.execute("""
                SELECT mbid, count(id)
                FROM lowlevel
                WHERE submitted <= %s
                GROUP BY mbid
                """, (start_time,))
            counts = cursor.fetchall()
            for count in counts:
                mbid_occurences[count[0]] = count[1]

        if start_time or end_time:
            start_cond = "submitted > '%s'" % str(start_time) if start_time else ''
            end_cond = "submitted <= '%s'" % str(end_time) if end_time else ''
            if start_time and end_time:
                where = "WHERE %s AND %s" % (start_cond, end_cond)
            else:
                where = "WHERE %s%s" % (start_cond, end_cond)
        else:
            where = ''
        cursor.execute("SELECT id FROM lowlevel ll %s ORDER BY mbid" % where)

        cursor_inner = db.cursor()
        temp_dir = tempfile.mkdtemp()

        dumped_count = 0

        while True:
            id_list = cursor.fetchmany(size=DUMP_CHUNK_SIZE)
            if not id_list:
                break
            id_list = tuple([i[0] for i in id_list])

            cursor_inner.execute("""SELECT mbid, data::text
                                    FROM lowlevel
                                    WHERE id IN %s
                                    ORDER BY mbid""", (id_list,))
            while True:
                row = cursor_inner.fetchone()
                if not row:
                    break
                mbid, json = row

                json_filename = mbid + "-%d.json" % mbid_occurences[mbid]
                dump_tempfile = os.path.join(temp_dir, json_filename)
                with open(dump_tempfile, "w") as f:
                    f.write(json)
                tar.add(dump_tempfile, arcname=os.path.join(
                    archive_name, "lowlevel", mbid[0:1], mbid[0:2], json_filename))
                os.unlink(dump_tempfile)

                mbid_occurences[mbid] += 1
                dumped_count += 1

        # Copying legal text
        tar.add(os.path.join("licenses", "COPYING-PublicDomain"),
                arcname=os.path.join(archive_name, 'COPYING'))

        shutil.rmtree(temp_dir)  # Cleanup

        print("Dumped %s tracks." % dumped_count)

    return archive_path


def dump_highlevel_json(location, incremental=False, dump_id=None):
    """Create JSON dump with high level data.

    Args:
        location: Directory where archive will be created.
        incremental: False if resulting JSON dump should be complete, False if
            it needs to be incremental.
        dump_id: If you need to reproduce previously created incremental dump,
            its identifier (integer) can be specified there.

    Returns:
        Path to created high level JSON dump.
    """
    create_path(location)

    if incremental:
        dump_id, start_time, end_time = _prepare_incremental_dump(dump_id)
        archive_name = 'acousticbrainz-highlevel-json-incr-%s' % dump_id
    else:
        start_time, end_time = None, None  # full
        archive_name = 'acousticbrainz-highlevel-json-%s' % \
                       datetime.today().strftime('%Y%m%d')

    archive_path = os.path.join(location, archive_name + '.tar.bz2')
    with tarfile.open(archive_path, "w:bz2") as tar:
        db = psycopg2.connect(current_app.config["PG_CONNECT"])
        cursor = db.cursor()

        mbid_occurences = defaultdict(int)

        # Need to count how many duplicate MBIDs are there before start_time
        if start_time:
            cursor.execute("""
                SELECT mbid, count(id)
                FROM highlevel
                WHERE submitted <= %s
                GROUP BY mbid
                """, (start_time,))
            counts = cursor.fetchall()
            for count in counts:
                mbid_occurences[count[0]] = count[1]

        if start_time or end_time:
            start_cond = "hl.submitted > '%s'" % str(start_time) if start_time else ''
            end_cond = "hl.submitted <= '%s'" % str(end_time) if end_time else ''
            if start_time and end_time:
                where = "AND %s AND %s" % (start_cond, end_cond)
            else:
                where = "AND %s%s" % (start_cond, end_cond)
        else:
            where = ''
        cursor.execute("""SELECT hl.id
                          FROM highlevel hl, highlevel_json hlj
                          WHERE hl.data = hlj.id %s
                          ORDER BY mbid""" % where)

        cursor_inner = db.cursor()
        temp_dir = tempfile.mkdtemp()

        dumped_count = 0

        while True:
            id_list = cursor.fetchmany(size=DUMP_CHUNK_SIZE)
            if not id_list:
                break
            id_list = tuple([i[0] for i in id_list])

            cursor_inner.execute("""SELECT mbid, hlj.data::text
                                    FROM highlevel hl, highlevel_json hlj
                                    WHERE hl.data = hlj.id AND hl.id IN %s
                                    ORDER BY mbid""", (id_list, ))
            while True:
                row = cursor_inner.fetchone()
                if not row:
                    break
                mbid, json = row

                json_filename = mbid + "-%d.json" % mbid_occurences[mbid]
                dump_tempfile = os.path.join(temp_dir, json_filename)
                with open(dump_tempfile, "w") as f:
                    f.write(json)
                tar.add(dump_tempfile, arcname=os.path.join(
                    archive_name, "highlevel", mbid[0:1], mbid[0:2], json_filename))
                os.unlink(dump_tempfile)

                mbid_occurences[mbid] += 1
                dumped_count += 1

        # Copying legal text
        tar.add(os.path.join("licenses", "COPYING-PublicDomain"),
                arcname=os.path.join(archive_name, 'COPYING'))

        shutil.rmtree(temp_dir)  # Cleanup

        print("Dumped %s tracks." % dumped_count)

    return archive_path


def list_incremental_dumps():
    """Get information about all created incremental dumps.

    Returns:
        List of (id, created) pairs ordered by dump identifier, or None if
        there are no incremental dumps yet.
    """
    cursor = psycopg2.connect(current_app.config["PG_CONNECT"]).cursor()
    cursor.execute("SELECT id, created FROM incremental_dumps ORDER BY id DESC")
    return cursor.fetchall()


def _prepare_incremental_dump(dump_id=None):
    if dump_id:  # getting existing
        existing_dumps = list_incremental_dumps()
        start_t, end_t = None, None
        if existing_dumps:
            for i, dump_info in enumerate(existing_dumps):
                if dump_info[0] == dump_id:
                    end_t = dump_info[1]
                    # Getting info about the dump before that specified
                    start_t = existing_dumps[i+1][1] if i+1 < len(existing_dumps) else None
                    break
        if not start_t and not end_t:
            raise Exception('Cannot find incremental dump with a specified ID.'
                            ' Please check if it exists or create a new one.')

    else:  # creating new
        start_t = _get_incremental_dump_timestamp()
        # TODO(roman): Check if there's any new data before creating new incremental dump
        dump_id, end_t = _create_new_inc_dump_record()

    return dump_id, start_t, end_t


def _create_new_inc_dump_record():
    """Creates new record for incremental dump and returns its ID and creation time."""
    db = psycopg2.connect(current_app.config["PG_CONNECT"])
    cursor = db.cursor()
    cursor.execute("INSERT INTO incremental_dumps (created) VALUES (now()) RETURNING id, created")
    db.commit()
    return cursor.fetchone()


def _get_incremental_dump_timestamp(dump_id=None):
    cursor = psycopg2.connect(current_app.config["PG_CONNECT"]).cursor()
    if dump_id:
        cursor.execute("SELECT created FROM incremental_dumps WHERE id = %s", (dump_id,))
    else:
        cursor.execute("SELECT created FROM incremental_dumps ORDER BY id DESC")
    row = cursor.fetchone()
    return row[0] if row else None
