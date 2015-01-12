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
}


def dump_db(location, threads=None):
    """Create complete database dump in a specified location.

    Args:
        location: Directory where archive will be created.
        threads: Maximal number of threads to run during compression.

    Returns:
        Path to created dump.
    """
    time_now = datetime.today()

    # Creating a directory where dump will go
    create_path(location)
    archive_path = os.path.join(location, 'acousticbrainzdump-%s.tar.xz' %
                                time_now.strftime('%Y%m%d-%H%M%S'))

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
            conn = psycopg2.connect(config.PG_CONNECT)
            cursor = conn.cursor()
            for table in _TABLES.keys():
                print(" - Dumping %s table..." % table)
                with open(os.path.join(archive_tables_dir, table), 'w') as f:
                    cursor.copy_to(f, table, columns=_TABLES[table])
            tar.add(archive_tables_dir, arcname='abdump')

            shutil.rmtree(temp_dir)  # Cleanup

        pxz.stdin.close()

    return archive_path


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
