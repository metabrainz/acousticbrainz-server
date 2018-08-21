"""
Functions for exporting and importing AcousticBrainz data in various formats.

There are two types of data dumps:
1. Full dumps (high/low level information about all recordings in JSON format
or raw information from all tables in TSV format).
2. Incremental dumps (similar to the first one, but some dumped tables don't
include information from the previous dumps).
"""
from __future__ import print_function
from collections import defaultdict
from datetime import datetime
from flask import current_app
import utils.path
import db
import subprocess
import tempfile
import logging
import tarfile
import shutil
import uuid
import os
from sqlalchemy import text


DUMP_CHUNK_SIZE = 1000
ROWS_PER_FILE = 500000
DUMP_LICENSE_FILE_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                      "licenses", "COPYING-PublicDomain")


# Importing of old dumps will fail if you change
# definition of columns below.
_TABLES = {
    "version": (
        "id",
        "data",
        "data_sha256",
        "type",
        "created",
    ),
    "lowlevel": (
        "id",
        "gid",
        "build_sha1",
        "lossless",
        "submitted",
        "gid_type",
    ),
    "lowlevel_json": (
        "id",
        "data",
        "data_sha256",
        "version",
    ),
    "model": (
        "id",
        "model",
        "model_version",
        "date",
        "status",
    ),
    "highlevel": (
        "id",
        "mbid",
        "build_sha1",
        "submitted",
    ),
    "highlevel_meta": (
        "id",
        "data",
        "data_sha256",
    ),
    "highlevel_model": (
        "id",
        "highlevel",
        "data",
        "data_sha256",
        "model",
        "version",
        "created",
    ),
    "statistics": (
        "name",
        "value",
        "collected",
    ),
    "incremental_dumps": (
        "id",
        "created",
    ),
}

_DATASET_TABLES = {
    "dataset": (
        "id",
        "name",
        "description",
        "author",
        "public",
        "created",
        "last_edited",
    ),
    "dataset_class": (
        "id",
        "name",
        "description",
        "dataset",
    ),
    "dataset_class_member": (
        "class",
        "mbid",
    ),
    "dataset_snapshot": (
        "id",
        "dataset_id",
        "data",
        "created",
    ),
    "dataset_eval_jobs": (
        "id",
        "snapshot_id",
        "status",
        "status_msg",
        "options",
        "training_snapshot",
        "testing_snapshot",
        "created",
        "updated",
        "result",
        "eval_location",
    ),
    "dataset_eval_sets": (
        "id",
        "data",
    ),
    "challenge": (
        "id",
        "name",
        "validation_snapshot",
        "creator",
        "created",
        "start_time",
        "end_time",
        "classes",
        "concluded",
    ),
    "dataset_eval_challenge":(
        "dataset_eval_job",
        "challenge_id",
        "result",
    ),
}


# this tuple contains the names of all the tables which
# are dumped into multiple file to save space while creating
# data dumps
# NOTE: make sure you append any tables to this when dumping them into
# multiple files.
PARTITIONED_TABLES = (
    "lowlevel_json",
    "highlevel_model",
)


def dump_db(location, threads=None, incremental=False, dump_id=None):
    """Create database dump in a specified location.

    Args:
        location: Directory where archive will be created.
        threads: Maximal number of threads to run during compression.
        incremental: False if resulting data dump should be complete, True if
            it needs to be incremental.
        dump_id: If you need to reproduce previously created incremental dump,
            its identifier (integer) can be specified there.

    Returns:
        Path to created dump.
    """
    utils.path.create_path(location)
    time_now = datetime.today()

    if incremental:
        dump_id, start_t, end_t = prepare_incremental_dump(dump_id)
        archive_name = "acousticbrainz-dump-incr-%s" % dump_id
    else:
        start_t, end_t = None, None  # full
        archive_name = "acousticbrainz-dump-%s" % time_now.strftime("%Y%m%d-%H%M%S")

    archive_path = os.path.join(location, archive_name + ".tar.xz")
    _dump_tables(
        archive_path=archive_path,
        threads=threads,
        dataset_dump=False,
        time_now=time_now,
        start_t=start_t,
        end_t=end_t,
    )
    return archive_path


def _copy_table_into_multiple_files(cursor, table_name, query, tar, archive_name):
    """Copies data from a table into multiple files and add them to the archive

    Args:
        cursor: a psycopg2 cursor
        table_name: the name of the table to be copied.
        query: the select query for getting data from the table, with appropriate LIMIT and OFFSET parameters.
        tar: the TarFile object to which the table dumps must be added
        archive_name: the name of the archive
    """
    location = tempfile.mkdtemp()
    offset = 0
    file_count = 0
    utils.path.create_path(os.path.join(location, table_name))
    while True:
        more_rows_added = False
        file_count += 1
        file_name = '{table_name}-{file_number}'.format(table_name=table_name, file_number=file_count)
        path = os.path.join(location, table_name, file_name)
        with open(path, "a") as f:
            logging.info(" - Copying table {table_name} to {file_name}...".format(table_name=table_name, file_name=file_name))
            current_query = query.format(limit=ROWS_PER_FILE, offset=offset)
            copy_query = 'COPY ({query}) TO STDOUT'.format(query=current_query)
            cursor.copy_expert(copy_query, f)
            offset += ROWS_PER_FILE
            if f.tell() > 0:
                more_rows_added = True
        if more_rows_added:
            tar.add(path,
                    arcname=os.path.join(archive_name, "abdump", table_name, file_name))

        os.remove(path)
        if not more_rows_added:
            break
    shutil.rmtree(location)


def _copy_table(cursor, location, table_name, query):
    """Copies data from a table into a file within a specified location.
    Args:
        cursor: a psycopg2 cursor
        location: the directory where the table should be copied.
        table_name: the name of the table to be copied.
        query: the select query for getting data from the table.
    """
    with open(os.path.join(location, table_name), "w") as f:
        logging.info(" - Copying table {table_name}...".format(table_name=table_name))
        print(" - Copying table {table_name}...".format(table_name=table_name))
        copy_query = 'COPY ({query}) TO STDOUT'.format(query=query)
        cursor.copy_expert(copy_query, f)


def _copy_dataset_tables(location, start_time=None, end_time=None):
    """ Copies datasets tables into seperate files withing a specified location (directory).
    """
    connection = db.engine.raw_connection()
    try:
        cursor = connection.cursor()
        # dataset
        _copy_table(cursor, location, "dataset", "SELECT %s FROM dataset" %
                    (", ".join(_DATASET_TABLES["dataset"])))

        # dataset_class
        _copy_table(cursor, location, "dataset_class", "SELECT %s FROM dataset_class" %
                    (", ".join(_DATASET_TABLES["dataset_class"])))

        # dataset_class_member
        _copy_table(cursor, location, "dataset_class_member", "SELECT %s FROM dataset_class_member" %
                    (", ".join(_DATASET_TABLES["dataset_class_member"])))

        # dataset_snapshot
        _copy_table(cursor, location, "dataset_snapshot", "SELECT %s FROM dataset_snapshot" %
                    (", ".join(_DATASET_TABLES["dataset_snapshot"])))

        # dataset_eval_jobs
        _copy_table(cursor, location, "dataset_eval_jobs", "SELECT %s FROM dataset_eval_jobs" %
                    (", ".join(_DATASET_TABLES["dataset_eval_jobs"])))

        # dataset_eval_sets
        _copy_table(cursor, location, "dataset_eval_sets", "SELECT %s FROM dataset_eval_sets" %
                    (", ".join(_DATASET_TABLES["dataset_eval_sets"])))

        # challenge
        _copy_table(cursor, location, "challenge", "SELECT %s FROM challenge" %
                    (", ".join(_DATASET_TABLES["challenge"])))

        # dataset_eval_challenge
        _copy_table(cursor, location, "dataset_eval_challenge", "SELECT %s FROM dataset_eval_challenge" %
                    (", ".join(_DATASET_TABLES["dataset_eval_challenge"])))
    finally:
        connection.close()


def _copy_tables(location, tar, archive_name, start_time=None, end_time=None):
    """Copies all core tables into separate files within a specified location (directory).

    NOTE: only copies tables in the variable _TABLES

    You can also define time frame that will be used during data selection.
    Files in a specified directory will only contain rows that have timestamps
    within specified time frame. We assume that each table contains some sort
    of timestamp that can be used as a reference.
    """
    def generate_where(row_name, start_t=start_time, end_t=end_time):
        """This function generates SQL WHERE clause that can be used to select
        rows only within specified time frame using `row_name` as a reference.
        """
        if start_t or end_t:
            start_cond = "%s > '%s'" % (row_name, str(start_t)) if start_t else ""
            end_cond = "%s <= '%s'" % (row_name, str(end_t)) if end_t else ""
            if start_t and end_t:
                return "WHERE %s AND %s" % (start_cond, end_cond)
            else:
                return "WHERE %s%s" % (start_cond, end_cond)
        else:
            return ""

    connection = db.engine.raw_connection()
    try:
        cursor = connection.cursor()
        # version
        _copy_table(cursor, location, "version", "SELECT %s FROM version %s" %
                    (", ".join(_TABLES["version"]), generate_where("created")))

        # lowlevel
        _copy_table(cursor, location, "lowlevel", "SELECT %s FROM lowlevel %s" %
                    (", ".join(_TABLES["lowlevel"]), generate_where("submitted")))

        # lowlevel_json
        query = "SELECT %s FROM lowlevel_json WHERE id IN (SELECT id FROM lowlevel %s) ORDER BY id LIMIT {limit} OFFSET {offset}" \
                % (", ".join(_TABLES["lowlevel_json"]), generate_where("submitted"))
        _copy_table_into_multiple_files(cursor, "lowlevel_json", query, tar, archive_name)

        # model
        query = "SELECT %s FROM model %s" \
                % (", ".join(_TABLES["model"]), generate_where("date"))
        _copy_table(cursor, location, "model", query)


        # highlevel
        _copy_table(cursor, location, "highlevel", "SELECT %s FROM highlevel %s" %
                    (", ".join(_TABLES["highlevel"]), generate_where("submitted")))

        # highlevel_meta
        query = "SELECT %s FROM highlevel_meta WHERE id IN (SELECT id FROM highlevel %s)" \
                % (", ".join(_TABLES["highlevel_meta"]), generate_where("submitted"))
        _copy_table(cursor, location, "highlevel_meta", query)

        # highlevel_model
        query = "SELECT %s FROM highlevel_model WHERE id IN (SELECT id FROM highlevel %s) ORDER BY id LIMIT {limit} OFFSET {offset}" \
                % (", ".join(_TABLES["highlevel_model"]), generate_where("submitted"))
        _copy_table_into_multiple_files(cursor, "highlevel_model", query, tar, archive_name)

        # statistics
        _copy_table(cursor, location, "statistics", "SELECT %s FROM statistics %s" %
                    (", ".join(_TABLES["statistics"]), generate_where("collected")))

        # incremental_dumps
        _copy_table(cursor, location, "incremental_dumps", "SELECT %s FROM incremental_dumps %s" %
                    (", ".join(_TABLES["incremental_dumps"]), generate_where("created")))
    finally:
        connection.close()


def _is_partitioned_table_dump_file(file_name):
    """ Checks if the specified file contains data for some table which has been
    dumped into multiple files.
    """
    for table in PARTITIONED_TABLES:
        if table in file_name:
            return True
    return False


def update_sequence(seq_name, table_name):
    """ Update the specified sequence's value to the maximum value of ID in the table.

    Args:
        seq_name (str): the name of the sequence to be updated.
        table_name (str): the name of the table from which the maximum value is to be retrieved
    """
    with db.engine.connect() as connection:
        connection.execute(text("""
            SELECT setval('{seq_name}', max(id))
              FROM {table_name}
        """.format(seq_name=seq_name, table_name=table_name)))


def update_sequences():
    """ Update all sequences to the maximum value of id in the table.
    """
    # lowlevel_id_seq
    current_app.logger.info('Updating lowlevel_id_seq...')
    update_sequence('lowlevel_id_seq', 'lowlevel')

    # highlevel_model_id_seq
    current_app.logger.info('Updating highlevel_model_id_seq...')
    update_sequence('highlevel_model_id_seq', 'highlevel')

    # version_id_seq
    current_app.logger.info('Updating version_id_seq...')
    update_sequence('version_id_seq', 'version')

    # model_id_seq
    current_app.logger.info('Updating model_id_seq...')
    update_sequence('model_id_seq', 'model')

    # incremental_dumps_id_seq
    current_app.logger.info('Updating incremental_dumps_id_seq...')
    update_sequence('incremental_dumps_id_seq', 'incremental_dumps')

    # user_id_seq
    current_app.logger.info('Updating user_id_seq...')
    update_sequence('user_id_seq', '"user"')

    # dataset_class_id_seq
    current_app.logger.info('Updating dataset_class_id_seq...')
    update_sequence('dataset_class_id_seq', 'dataset_class')

    # dataset_eval_sets_id_seq
    current_app.logger.info('Updating dataset_eval_sets_id_seq...')
    update_sequence('dataset_eval_sets_id_seq', 'dataset_eval_sets')


def import_db_dump(archive_path, tables):
    """Import data from .tar.xz archive into the database."""
    pxz_command = ["pxz", "--decompress", "--stdout", archive_path]
    pxz = subprocess.Popen(pxz_command, stdout=subprocess.PIPE)

    table_names = tables.keys()

    connection = db.engine.raw_connection()
    try:
        cursor = connection.cursor()

        with tarfile.open(fileobj=pxz.stdout, mode="r|") as tar:
            for member in tar:
                file_name = member.name.split("/")[-1]

                if file_name == "SCHEMA_SEQUENCE":
                    # Verifying schema version
                    schema_seq = int(tar.extractfile(member).read().strip())
                    if schema_seq != db.SCHEMA_VERSION:
                        raise Exception("Incorrect schema version! Expected: %d, got: %d."
                                        "Please, get the latest version of the dump."
                                        % (db.SCHEMA_VERSION, schema_seq))
                    else:
                        logging.info("Schema version verified.")

                else:
                    if _is_partitioned_table_dump_file(file_name):
                        table_name = member.name.split("/")[2]
                        logging.info(" - Importing data from file %s into %s table..." % (file_name, table_name))
                        cursor.copy_from(tar.extractfile(member), '"%s"' % table_name,
                                        columns=_TABLES[table_name])

                    elif file_name in table_names:
                        logging.info(" - Importing data into %s table..." % file_name)
                        cursor.copy_from(tar.extractfile(member), '"%s"' % file_name,
                                         columns=tables[file_name])
        connection.commit()
    finally:
        connection.close()

    pxz.stdout.close()
    pxz.wait()

    logging.info('Updating sequences...')
    update_sequences()
    logging.info('Done!')


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
    utils.path.create_path(location)

    if incremental:
        dump_id, start_time, end_time = prepare_incremental_dump(dump_id)
        archive_name = "acousticbrainz-lowlevel-json-incr-%s" % dump_id
    else:
        start_time, end_time = None, None  # full
        archive_name = "acousticbrainz-lowlevel-json-%s" % \
                       datetime.today().strftime("%Y%m%d")

    archive_path = os.path.join(location, archive_name + ".tar.bz2")
    with tarfile.open(archive_path, "w:bz2") as tar:

        connection = db.engine.raw_connection()
        try:
            cursor = connection.cursor()

            mbid_occurences = defaultdict(int)

            # Need to count how many duplicate MBIDs are there before start_time
            if start_time:
                cursor.execute("""
                    SELECT gid, count(id)
                    FROM lowlevel
                    WHERE submitted <= %s
                    GROUP BY gid
                    """, (start_time,))
                counts = cursor.fetchall()
                for mbid, count in counts:
                    mbid_occurences[mbid] = count

            if start_time or end_time:
                start_cond = "submitted > '%s'" % str(start_time) if start_time else ""
                end_cond = "submitted <= '%s'" % str(end_time) if end_time else ""
                if start_time and end_time:
                    where = "WHERE %s AND %s" % (start_cond, end_cond)
                else:
                    where = "WHERE %s%s" % (start_cond, end_cond)
            else:
                where = ""
            cursor.execute("SELECT id FROM lowlevel ll %s ORDER BY gid" % where)

            cursor_inner = connection.cursor()

            temp_dir = tempfile.mkdtemp()

            dumped_count = 0

            while True:
                id_list = cursor.fetchmany(size=DUMP_CHUNK_SIZE)
                if not id_list:
                    break
                id_list = tuple([i[0] for i in id_list])

                query = text("""
                   SELECT gid::text
                        , llj.data::text
                     FROM lowlevel ll
                     JOIN lowlevel_json llj
                       ON ll.id = llj.id
                    WHERE ll.id IN :id_list
                """)

                cursor_inner.execute(query, {"id_list": id_list})

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
        finally:
            connection.close()

        # Copying legal text
        tar.add(DUMP_LICENSE_FILE_PATH,
                arcname=os.path.join(archive_name, "COPYING"))

        shutil.rmtree(temp_dir)  # Cleanup

        logging.info("Dumped %s recordings." % dumped_count)

    return archive_path


def dump_highlevel_json(location, incremental=False, dump_id=None):
    """Create JSON dump with high-level data.

    Args:
        location: Directory where archive will be created.
        incremental: False if resulting JSON dump should be complete, False if
            it needs to be incremental.
        dump_id: If you need to reproduce previously created incremental dump,
            its identifier (integer) can be specified there.

    Returns:
        Path to created high-level JSON dump.
    """
    utils.path.create_path(location)

    if incremental:
        dump_id, start_time, end_time = prepare_incremental_dump(dump_id)
        archive_name = "acousticbrainz-highlevel-json-incr-%s" % dump_id
    else:
        start_time, end_time = None, None  # full
        archive_name = "acousticbrainz-highlevel-json-%s" % \
                       datetime.today().strftime("%Y%m%d")

    archive_path = os.path.join(location, archive_name + ".tar.bz2")
    with tarfile.open(archive_path, "w:bz2") as tar:

        with db.engine.connect() as connection:
            mbid_occurences = defaultdict(int)

            # Need to count how many duplicate MBIDs are there before start_time
            if start_time:
                result = connection.execute("""
                    SELECT mbid, count(id)
                    FROM highlevel
                    WHERE submitted <= %s
                    GROUP BY mbid
                    """, (start_time,))
                counts = result.fetchall()
                for mbid, count in counts:
                    mbid_occurences[mbid] = count

            if start_time or end_time:
                start_cond = "hl.submitted > '%s'" % str(start_time) if start_time else ""
                end_cond = "hl.submitted <= '%s'" % str(end_time) if end_time else ""
                if start_time and end_time:
                    where = "AND %s AND %s" % (start_cond, end_cond)
                else:
                    where = "AND %s%s" % (start_cond, end_cond)
            else:
                where = ""
            result = connection.execute("""SELECT hl.id
                              FROM highlevel hl, highlevel_json hlj
                              WHERE hl.data = hlj.id %s
                              ORDER BY mbid""" % where)

            with db.engine.connect() as connection_inner:
                temp_dir = tempfile.mkdtemp()

                dumped_count = 0

                while True:
                    id_list = result.fetchmany(size=DUMP_CHUNK_SIZE)
                    if not id_list:
                        break
                    id_list = tuple([i[0] for i in id_list])

                    q = text("""SELECT mbid::text, hlj.data::text
                           FROM highlevel hl, highlevel_json hlj
                           WHERE hl.data = hlj.id AND hl.id IN :ids
                           ORDER BY mbid""")
                    result_inner = connection_inner.execute(q, {"ids": id_list})
                    while True:
                        row = result_inner.fetchone()
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
        tar.add(DUMP_LICENSE_FILE_PATH,
                arcname=os.path.join(archive_name, "COPYING"))

        shutil.rmtree(temp_dir)  # Cleanup

        logging.info("Dumped %s recordings." % dumped_count)

    return archive_path


def list_incremental_dumps():
    """Get information about all created incremental dumps.

    Returns:
        List of (id, created) pairs ordered by dump identifier, or None if
        there are no incremental dumps yet.
    """
    with db.engine.connect() as connection:
        result = connection.execute("SELECT id, created FROM incremental_dumps ORDER BY id DESC")
        return result.fetchall()


def prepare_incremental_dump(dump_id=None):
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
            raise Exception("Cannot find incremental dump with a specified ID."
                            " Please check if it exists or create a new one.")

    else:  # creating new
        start_t = _get_incremental_dump_timestamp()
        if start_t and not _any_new_data(start_t):
            raise NoNewData("No new data since the last incremental dump!")
        dump_id, end_t = _create_new_inc_dump_record()

    return dump_id, start_t, end_t


def _any_new_data(from_time):
    """Checks if there's any new data since specified time in tables that
    support incremental dumps.

    Returns:
        True if there is new data in one of tables that support incremental
        dumps, False if there is no new data there.
    """
    with db.engine.connect() as connection:
        result = connection.execute("SELECT count(*) FROM lowlevel WHERE submitted > %s", (from_time,))
        lowlevel_count = result.fetchone()[0]
        result = connection.execute("SELECT count(*) FROM highlevel WHERE submitted > %s", (from_time,))
        highlevel_count = result.fetchone()[0]
    return lowlevel_count > 0 or highlevel_count > 0


def _create_new_inc_dump_record():
    """Creates new record for incremental dump and returns its ID and creation time."""
    with db.engine.connect() as connection:
        result = connection.execute("INSERT INTO incremental_dumps (created) VALUES (now()) RETURNING id, created")
        row = result.fetchone()
    logging.info("Created new incremental dump record (ID: %s)." % row[0])
    return row


def _get_incremental_dump_timestamp(dump_id=None):
    with db.engine.connect() as connection:
        if dump_id:
            result = connection.execute("SELECT created FROM incremental_dumps WHERE id = %s", (dump_id,))
        else:
            result = connection.execute("SELECT created FROM incremental_dumps ORDER BY id DESC")
        row = result.fetchone()
    return row[0] if row else None


class NoNewData(Exception):
    pass


def _dump_tables(archive_path, threads, dataset_dump, time_now, start_t=None, end_t=None):
    """Copies the metadata and the tables to the archive.

    Args:
        archive_path (str): Complete path of the archive that will be created.
        threads (int): Maximal number of threads to run during compression.
        dataset_dump (bool): If true, only dataset tables are copied to the archive.
        time_now (datetime): Current time.
        start_t (datetime): Start time of the frame that will be used for data selection. (in incremental dumps)
        end_t (datetime): End time of the frame that will be used for data selection.
    """
    archive_name = os.path.basename(archive_path).split('.')[0]
    with open(archive_path, "w") as archive:

        pxz_command = ["pxz", "--compress"]
        if threads is not None:
            pxz_command.append("-T %s" % threads)
        pxz = subprocess.Popen(pxz_command, stdin=subprocess.PIPE, stdout=archive)

        # Creating the archive
        with tarfile.open(fileobj=pxz.stdin, mode="w|") as tar:
            # TODO: Get rid of temporary directories and write directly to tar file if that's possible
            temp_dir = tempfile.mkdtemp()

            # Adding metadata
            schema_seq_path = os.path.join(temp_dir, "SCHEMA_SEQUENCE")
            with open(schema_seq_path, "w") as f:
                f.write(str(db.SCHEMA_VERSION))
            tar.add(schema_seq_path,
                    arcname=os.path.join(archive_name, "SCHEMA_SEQUENCE"))
            timestamp_path = os.path.join(temp_dir, "TIMESTAMP")
            with open(timestamp_path, "w") as f:
                f.write(time_now.isoformat(" "))
            tar.add(timestamp_path,
                    arcname=os.path.join(archive_name, "TIMESTAMP"))
            tar.add(DUMP_LICENSE_FILE_PATH,
                    arcname=os.path.join(archive_name, "COPYING"))

            archive_tables_dir = os.path.join(temp_dir, "abdump", "abdump")
            utils.path.create_path(archive_tables_dir)
            if dataset_dump:
                _copy_dataset_tables(archive_tables_dir, start_t, end_t)
            else:
                _copy_tables(archive_tables_dir,tar, archive_name, start_t, end_t)
            tar.add(archive_tables_dir, arcname=os.path.join(archive_name, "abdump"))

            shutil.rmtree(temp_dir)

        pxz.stdin.close()
        pxz.wait()


def dump_dataset_tables(location, threads=None):
    """Create full dump of dataset tables in a specified location.

    Args:
        location: Directory where archive will be created.
    Returns:
        Path to created dump.
    """
    utils.path.create_path(location)
    time_now = datetime.today()
    archive_name = "acousticbrainz-dataset-dump-%s" % time_now.strftime("%Y%m%d-%H%M%S")

    archive_path = os.path.join(location, archive_name + ".tar.xz")
    _dump_tables(
        archive_path=archive_path,
        threads=threads,
        dataset_dump=True,
        time_now=time_now,
    )
    return archive_path


def import_dump(archive_path):
    """Imports a database dump from .tar.xz archive into the database."""
    import_db_dump(archive_path, _TABLES)


def import_datasets_dump(archive_path):
    """Import datasets from .tar.xz archive into the database."""
    import_db_dump(archive_path, _DATASET_TABLES)


def _is_valid_uuid(text):
    try:
        x = uuid.UUID(text)
        return True
    except ValueError:
        return False
