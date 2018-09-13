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
import os
from sqlalchemy import text


DUMP_CHUNK_SIZE = 1000
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
    "data_dump": (
        "id",
        "created",
        "dump_type",
    ),
}


def dump_db(location, threads=None, full=False, dump_id=None):
    """Create database dump in a specified location.

    Args:
        location: Directory where archive will be created.
        threads: Maximal number of threads to run during compression.
        full (bool): True if you want to dump the entire db from the beginning of time, False if
                only need to dump new data since the last dump.
        dump_id: If you need to reproduce previously created incremental dump,
            its identifier (integer) can be specified there.

    Returns:
        Path to created dump.
    """
    utils.path.create_path(location)

    if dump_id:
        dump_id, start_time, end_time, full = prepare_dump(dump_id=dump_id)
    else:
        dump_id, start_time, end_time, full = prepare_dump(full=full)

    if full:
        archive_name = "acousticbrainz-dump-full-%s-%s" % (dump_id, end_time.strftime("%Y%m%d-%H%M%S"))
    else:
        full_dump_timestamp = _get_last_full_dump_timestamp(dump_id)
        archive_name = "acousticbrainz-dump-incr-%s-%s" % (dump_id, full_dump_timestamp.strftime("%Y%m%d-%H%M%S"))

    archive_path = os.path.join(location, archive_name + ".tar.xz")
    with open(archive_path, "w") as archive:

        pxz_command = ["pxz", "--compress"]
        if threads is not None:
            pxz_command.append("-T %s" % threads)
        pxz = subprocess.Popen(pxz_command, stdin=subprocess.PIPE, stdout=archive)

        # Creating the archive
        with tarfile.open(fileobj=pxz.stdin, mode="w|") as tar:
            # TODO(roman): Get rid of temporary directories and write directly to tar file if that's possible.
            temp_dir = tempfile.mkdtemp()

            # Adding metadata
            schema_seq_path = os.path.join(temp_dir, "SCHEMA_SEQUENCE")
            with open(schema_seq_path, "w") as f:
                f.write(str(db.SCHEMA_VERSION))
            tar.add(schema_seq_path,
                    arcname=os.path.join(archive_name, "SCHEMA_SEQUENCE"))
            timestamp_path = os.path.join(temp_dir, "TIMESTAMP")
            with open(timestamp_path, "w") as f:
                f.write(end_time.isoformat(" "))
            tar.add(timestamp_path,
                    arcname=os.path.join(archive_name, "TIMESTAMP"))
            tar.add(DUMP_LICENSE_FILE_PATH,
                    arcname=os.path.join(archive_name, "COPYING"))

            archive_tables_dir = os.path.join(temp_dir, "abdump", "abdump")
            utils.path.create_path(archive_tables_dir)
            _copy_tables(archive_tables_dir, start_time, end_time)
            tar.add(archive_tables_dir, arcname=os.path.join(archive_name, "abdump"))

            shutil.rmtree(temp_dir)  # Cleanup

        pxz.stdin.close()

    return archive_path


def _copy_tables(location, start_time=None, end_time=None):
    """Copies all tables into separate files within a specified location (directory).

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
        with open(os.path.join(location, "version"), "w") as f:
            logging.info(" - Copying table version...")
            cursor.copy_to(f, "(SELECT %s FROM version %s)" %
                           (", ".join(_TABLES["version"]), generate_where("created")))

        # lowlevel
        with open(os.path.join(location, "lowlevel"), "w") as f:
            logging.info(" - Copying table lowlevel...")
            cursor.copy_to(f, "(SELECT %s FROM lowlevel %s)" %
                           (", ".join(_TABLES["lowlevel"]), generate_where("submitted")))

        # lowlevel_json
        with open(os.path.join(location, "lowlevel_json"), "w") as f:
            logging.info(" - Copying table lowlevel_json...")
            query = "SELECT %s FROM lowlevel_json WHERE id IN (SELECT id FROM lowlevel %s)" \
                    % (", ".join(_TABLES["lowlevel_json"]), generate_where("submitted"))
            cursor.copy_to(f, "(%s)" % query)

        # model
        with open(os.path.join(location, "model"), "w") as f:
            logging.info(" - Copying table model...")
            query = "SELECT %s FROM model %s" \
                    % (", ".join(_TABLES["model"]), generate_where("date"))
            cursor.copy_to(f, "(%s)" % query)


        # highlevel
        with open(os.path.join(location, "highlevel"), "w") as f:
            logging.info(" - Copying table highlevel...")
            cursor.copy_to(f, "(SELECT %s FROM highlevel %s)" %
                           (", ".join(_TABLES["highlevel"]), generate_where("submitted")))

        # highlevel_meta
        with open(os.path.join(location, "highlevel_meta"), "w") as f:
            logging.info(" - Copying table highlevel_meta...")
            query = "SELECT %s FROM highlevel_meta WHERE id IN (SELECT id FROM highlevel %s)" \
                    % (", ".join(_TABLES["highlevel_meta"]), generate_where("submitted"))
            cursor.copy_to(f, "(%s)" % query)

        # highlevel_model
        with open(os.path.join(location, "highlevel_model"), "w") as f:
            logging.info(" - Copying table highlevel_model...")
            query = "SELECT %s FROM highlevel_model WHERE id IN (SELECT id FROM highlevel %s)" \
                    % (", ".join(_TABLES["highlevel_model"]), generate_where("submitted"))
            cursor.copy_to(f, "(%s)" % query)

        # statistics
        with open(os.path.join(location, "statistics"), "w") as f:
            logging.info(" - Copying table statistics...")
            cursor.copy_to(f, "(SELECT %s FROM statistics %s)" %
                           (", ".join(_TABLES["statistics"]), generate_where("collected")))

        # data_dump
        with open(os.path.join(location, "data_dump"), "w") as f:
            logging.info(" - Copying table data_dump...")
            cursor.copy_to(f, "(SELECT %s FROM data_dump %s)" %
                           (", ".join(_TABLES["data_dump"]), generate_where("created")))
    finally:
        connection.close()


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

    # data_dump_id_seq
    current_app.logger.info('Updating data_dump_id_seq...')
    update_sequence('data_dump_id_seq', 'data_dump')

    # user_id_seq
    current_app.logger.info('Updating user_id_seq...')
    update_sequence('user_id_seq', '"user"')

    # dataset_class_id_seq
    current_app.logger.info('Updating dataset_class_id_seq...')
    update_sequence('dataset_class_id_seq', 'dataset_class')

    # dataset_eval_sets_id_seq
    current_app.logger.info('Updating dataset_eval_sets_id_seq...')
    update_sequence('dataset_eval_sets_id_seq', 'dataset_eval_sets')


def import_db_dump(archive_path):
    """Import data from .tar.xz archive into the database."""
    pxz_command = ["pxz", "--decompress", "--stdout", archive_path]
    pxz = subprocess.Popen(pxz_command, stdout=subprocess.PIPE)

    table_names = _TABLES.keys()

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
                    if file_name in table_names:
                        logging.info(" - Importing data into %s table..." % file_name)
                        cursor.copy_from(tar.extractfile(member), '"%s"' % file_name,
                                         columns=_TABLES[file_name])
        connection.commit()
    finally:
        connection.close()

    pxz.stdout.close()
    pxz.wait()

    logging.info('Updating sequences...')
    update_sequences()
    logging.info('Done!')


def dump_lowlevel_json(location, full=False, dump_id=None):
    """Create JSON dump with low level data.

    Args:
        location: Directory where archive will be created.
        full (bool): True if you want to dump the entire db from the beginning of time, False if
                only need to dump new data since the last dump.
        incremental: False if resulting JSON dump should be complete, False if
            it needs to be incremental.
        dump_id: If you need to reproduce previously created incremental dump,
            its identifier (integer) can be specified there.

    Returns:
        Path to created low level JSON dump.
    """
    utils.path.create_path(location)

    if dump_id:
        dump_id, start_time, end_time, full = prepare_dump(dump_id=dump_id)
    else:
        dump_id, start_time, end_time, full = prepare_dump(full=full)

    if full:
        archive_name = "acousticbrainz-lowlevel-json-full-%s-%s" % (dump_id, end_time.strftime("%Y%m%d-%H%M%S"))
    else:
        full_dump_timestamp = _get_last_full_dump_timestamp(dump_id)
        archive_name = "acousticbrainz-highlevel-json-incr-%s-%s" % (dump_id, full_dump_timestamp.strftime("%Y%m%d-%H%M%S"))

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


def dump_highlevel_json(location, full=False, dump_id=None):
    """Create JSON dump with high-level data.

    Args:
        location: Directory where archive will be created.
        full (bool): True if you want to dump the entire db from the beginning of time, False if
                only need to dump new data since the last dump.
        dump_id: If you need to reproduce previously created incremental dump,
            its identifier (integer) can be specified there.

    Returns:
        Path to created high-level JSON dump.
    """
    utils.path.create_path(location)

    if dump_id:
        dump_id, start_time, end_time, full = prepare_dump(dump_id=dump_id)
    else:
        dump_id, start_time, end_time, full = prepare_dump(full=full)

    if full:
        archive_name = "acousticbrainz-highlevel-json-full-%s-%s" % (dump_id, end_time.strftime("%Y%m%d-%H%M%S"))
    else:
        full_dump_timestamp = _get_last_full_dump_timestamp(dump_id)
        archive_name = "acousticbrainz-highlevel-json-incr-%s-%s" % (dump_id, full_dump_timestamp.strftime("%Y%m%d-%H%M%S"))

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


def list_dumps():
    """Get information about all created dumps.

    Returns:
        List of (id, created) pairs ordered by dump identifier, or None if
        there are no dumps yet.
    """
    with db.engine.connect() as connection:
        result = connection.execute("SELECT id, created, dump_type FROM data_dump ORDER BY id DESC")
        return result.fetchall()


def get_dump_info(dump_id):
    with db.engine.connect() as connection:
        result = connection.execute(text("""
            SELECT id, created, dump_type
              FROM data_dump
             WHERE id = :dump_id
        """), {
            "dump_id": dump_id,
        })
        if result.rowcount > 0:
            return dict(result.fetchone())
        else:
            return None


def prepare_dump(dump_id=None, full=False):
    if dump_id:  # getting existing
        existing_dumps = list_dumps()
        start_t, end_t = None, None
        if existing_dumps:
            for i, dump_info in enumerate(existing_dumps):
                if dump_info["id"] == dump_id:
                    end_t = dump_info["created"]
                    if dump_info["dump_type"] == "full":
                        start_t = None
                        full = True
                    else:
                        # Getting info about the dump before that specified
                        start_t = existing_dumps[i+1]["created"] if i+1 < len(existing_dumps) else None
                        full = False
                    break
        if not start_t and not end_t:
            raise Exception("Cannot find dump with a specified ID."
                            " Please check if it exists or create a new one.")

    else:  # creating new
        start_t = _get_dump_timestamp() if not full else None
        if start_t and not _any_new_data(start_t):
            raise NoNewData("No new data since the last dump!")
        dump_id, end_t = _create_new_dump_record(full=full)

    return dump_id, start_t, end_t, full


def _any_new_data(from_time):
    """Checks if there's any new data since specified time in tables that
    support dumps.

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


def _create_new_dump_record(full=False):
    """Creates new record for dump and returns its ID and creation time."""
    with db.engine.connect() as connection:
        result = connection.execute(text("""
            INSERT INTO data_dump (created, dump_type)
                 VALUES (now(), :dump_type)
              RETURNING id, created
            """), {
                "dump_type": "full" if full else "partial",
            })
        row = result.fetchone()
    logging.info("Created new incremental dump record (ID: %s)." % row[0])
    return row


def _get_dump_timestamp(dump_id=None):
    with db.engine.connect() as connection:
        if dump_id:
            result = connection.execute("SELECT created FROM data_dump WHERE id = %s", (dump_id,))
        else:
            result = connection.execute("SELECT created FROM data_dump ORDER BY id DESC")
        row = result.fetchone()
    return row[0] if row else None


def _get_last_full_dump_timestamp(dump_id):
    with db.engine.connect() as connection:
        result = connection.execute(text("""
            SELECT created
              FROM data_dump
             WHERE id < :dump_id
               AND dump_type = 'full'
          ORDER BY id DESC
             LIMIT 1
        """), {
            "dump_id": dump_id,
        })
        if result.rowcount > 0:
            return result.fetchone()[0]
        else:
            raise NoPreviousFullDump


class NoNewData(Exception):
    pass


class NoPreviousFullDump(Exception):
    pass
