from __future__ import print_function
from flask_script import Manager
from datetime import datetime
import acousticbrainz
import subprocess
import tarfile
import psycopg2
import shutil
import errno
import sys
import os
import re

app = acousticbrainz.create_app()
manager = Manager(app)

db_connection = psycopg2.connect(app.config['PG_CONNECT'])

# Importing of old dumps will fail if you change
# definition of tables below.
_tables = (
    (
        'lowlevel',
        (
            'id',
            'mbid',
            'build_sha1',
            'lossless',
            'data',
            'submitted',
            'data_sha256',
        )
    ),
    (
        'highlevel',
        (
            'id',
            'mbid',
            'build_sha1',
            'data',
            'submitted',
        )
    ),
    (
        'highlevel_json',
        (
            'id',
            'data',
            'data_sha256',
        )
    ),
    (
        'statistics',
        (
            'name',
            'value',
            'collected',
        )
    ),
)


@manager.command
def init_db(archive):
    """Initializes database and imports data if needed.

    This process involves several steps:
    1. Table structure is created.
    2. Data is imported from the dump if it exists.
    3. Primary keys and foreign keys are created.
    3. Indexes are created.

    Data dump needs to be a .tar.xz archive produced by export command.

    More information about populating a PostgreSQL database efficently can be
    found at http://www.postgresql.org/docs/current/static/populate.html.
    """
    print('Creating tables...')
    _run_sql_script('admin/sql/create_tables.sql')

    # TODO: Make importing optional
    print('Importing data...')
    _import_data(archive)

    print('Creating primary and foreign keys...')
    _run_sql_script('admin/sql/create_primary_keys.sql')
    _run_sql_script('admin/sql/create_foreign_keys.sql')

    print('Creating indexes...')
    _run_sql_script('admin/sql/create_indexes.sql')

    print("Done!")


@manager.command
def export(location=os.path.join(os.getcwd(), 'export'), threads=None, rotate=False):
    print("Creating new archives...")
    time_now = datetime.today()

    # Getting psycopg2 cursor
    cursor = db_connection.cursor()

    # Creating a directory where all dumps will go
    dump_dir = '%s/%s' % (location, time_now.strftime('%Y%m%d-%H%M%S'))
    temp_dir = '%s/temp' % dump_dir
    create_path(temp_dir)

    # Preparing meta files
    with open('%s/TIMESTAMP' % temp_dir, 'w') as f:
        f.write(time_now.isoformat(' '))
    with open('%s/SCHEMA_SEQUENCE' % temp_dir, 'w') as f:
        f.write(str(acousticbrainz.__version__))

    # Creating the archive
    with tarfile.open("%s/abdump.tar" % dump_dir, "w") as tar:
        base_archive_dir = '%s/abdump' % temp_dir
        create_path(base_archive_dir)

        base_archive_tables_dir = '%s/abdump' % base_archive_dir
        create_path(base_archive_tables_dir)
        for table in _tables:
            with open('%s/%s' % (base_archive_tables_dir, table[0]), 'w') as f:
                cursor.copy_to(f, table[0], columns=table[1])
        tar.add(base_archive_tables_dir, arcname='abdump')

        # Including additional information about this archive
        tar.add('licenses/COPYING-PublicDomain', arcname='COPYING')
        tar.add('%s/TIMESTAMP' % temp_dir, arcname='TIMESTAMP')
        tar.add('%s/SCHEMA_SEQUENCE' % temp_dir, arcname='SCHEMA_SEQUENCE')

    # Compressing created archive using pxz
    pxz_command = ['pxz', '-z', '%s/abdump.tar' % dump_dir]
    if threads is not None:
        pxz_command.append('-T %s' % threads)
    print(pxz_command)
    subprocess.check_call(pxz_command)
    print(" + %s/abdump.tar.xz" % dump_dir)

    shutil.rmtree(temp_dir)  # Cleanup

    if rotate:
        print("Removing old dumps (except two latest)...")
        remove_old_archives(location, "[0-9]+-[0-9]+", is_dir=True)

    print("Done!")


def _run_sql_script(sql_file):
    cursor = db_connection.cursor()
    with open(sql_file) as sql:
        cursor.execute(sql.read())


def _import_data(archive):
    subprocess.check_call(['pxz', '-d', '-k', archive])
    tar_file_path = archive[:-3]  # removing ".xz" extension
    with tarfile.open(tar_file_path, 'r') as tar:

        # Verifying schema version
        version = tar.extractfile('SCHEMA_SEQUENCE').readline()
        if str(acousticbrainz.__version__) != version:
            sys.exit("Incorrect schema version! Expected: %d, got: %c."
                     "Please, get latest version of the dump."
                     % (acousticbrainz.__version__, version))

        # Importing data
        cursor = db_connection.cursor()
        for table in _tables:
            print("Importing data into %s table." % table[0])
            try:
                f = tar.extractfile('abdump/%s' % table[0])
                cursor.copy_from(f, '"%s"' % table[0], columns=table[1])
                db_connection.commit()
            except IOError as exception:
                if exception.errno == errno.ENOENT:
                    print("Can't find data file for %s table. Skipping." % table[0])
                else:
                    sys.exit("Failed to open data file. Error: %s" % exception)
    os.remove(tar_file_path)  # Cleanup


def create_path(path):
    """Creates a directory structure if it doesn't exist yet."""
    try:
        os.makedirs(path)
    except OSError as exception:
        if exception.errno != errno.EEXIST:
            sys.exit("Failed to create directory structure %s. Error: %s" % (path, exception))


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
