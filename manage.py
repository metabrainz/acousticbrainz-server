from __future__ import print_function
from flask_script import Manager
from datetime import datetime
import acousticbrainz
import subprocess
import tempfile
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
# definition of columns below.
_tables = {
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
    print("Creating new archive...")
    time_now = datetime.today()

    # Creating a directory where dump will go
    create_path(location)
    archive_path = '%s/abdump-%s.tar.xz' % (location, time_now.strftime('%Y%m%d-%H%M%S'))
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
            with open('%s/SCHEMA_SEQUENCE' % temp_dir, 'w') as f:
                f.write(str(acousticbrainz.__version__))
            tar.add('%s/SCHEMA_SEQUENCE' % temp_dir, arcname='SCHEMA_SEQUENCE')
            with open('%s/TIMESTAMP' % temp_dir, 'w') as f:
                f.write(time_now.isoformat(' '))
            tar.add('%s/TIMESTAMP' % temp_dir, arcname='TIMESTAMP')
            tar.add('licenses/COPYING-PublicDomain', arcname='COPYING')

            archive_dir = '%s/abdump' % temp_dir
            archive_tables_dir = '%s/abdump' % archive_dir
            create_path(archive_tables_dir)
            cursor = db_connection.cursor()
            for table in _tables.keys():
                print(" - Dumping %s table..." % table)
                with open('%s/%s' % (archive_tables_dir, table), 'w') as f:
                    cursor.copy_to(f, table, columns=_tables[table])
            tar.add(archive_tables_dir, arcname='abdump')

            shutil.rmtree(temp_dir)  # Cleanup

        pxz.stdin.close()

    print("Database dump created:\n +", archive_path)

    if rotate:
        print("Removing old dumps (except two latest)...")
        remove_old_archives(location, "abdump-[0-9]+-[0-9]+.tar.xz",
                            is_dir=False, sort_key=lambda x: os.path.getmtime(x))

    print("Done!")


def _run_sql_script(sql_file):
    cursor = db_connection.cursor()
    with open(sql_file) as sql:
        cursor.execute(sql.read())


def _import_data(archive):
    pxz_command = ['pxz', '--decompress', '--stdout', archive]
    pxz = subprocess.Popen(pxz_command, stdout=subprocess.PIPE)

    with tarfile.open(fileobj=pxz.stdout, mode='r|') as tar:
        members = tar.getmembers()

        # Verifying schema version
        item = members.pop(0)
        if item.name == 'SCHEMA_SEQUENCE':
            version = tar.extractfile(item).readline()
            if str(acousticbrainz.__version__) != version:
                sys.exit("Incorrect schema version! Expected: %d, got: %c."
                         "Please, get the latest version of the dump."
                         % (acousticbrainz.__version__, version))
            else:
                print("Schema version verified.")
        else:
            sys.exit("Incorrect data dump structure! Please get the latest"
                     "version of the dump.")

        # Importing data
        table_names = _tables.keys()
        cursor = db_connection.cursor()
        for item in members:
            file_name = item.name.split('/')[-1]
            print(item.name, file_name)
            if file_name in table_names:
                print(" - Importing data into %s table..." % file_name)
                f = tar.extractfile(item.name)
                print(f)
                cursor.copy_from(f, '"%s"' % file_name, columns=_tables[file_name])
        db_connection.commit()

    pxz.stdout.close()


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
