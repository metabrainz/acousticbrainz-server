"""
Functions for exporting and importing AcousticBrainz data in various formats.

There are two types of data dumps:
1. Full dumps (high/low level information about all recordings in JSON format
or raw information from all tables in TSV format).
2. Incremental dumps (similar to the first one, but some dumped tables don't
include information from the previous dumps).
"""

import csv
from flask import current_app
import ujson

import utils.path
import db
import logging
import os
import shutil
import sqlalchemy
import subprocess
import tarfile
import tempfile
import json

from collections import defaultdict
from datetime import datetime
from sqlalchemy import text

# The number of items in a sample dataset
SAMPLE_DATASET_SIZE = 100000

# the number of rows to dump for json dumps in one batch
DUMP_CHUNK_SIZE = 10000

# Create multiple files of no more than this many rows for the
# big tables (lowlevel_json, highlevel_model) for the database dump
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
        "submission_offset",
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
        "class_mapping",
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
        "stats",
        "collected",
    ),
    "data_dump": (
        "id",
        "created",
        "dump_type",
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
    "dataset_eval_challenge": (
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

LOWLEVEL_FEATURES_TONAL = {
    "key_key": "'tonal'->>'key_key'",
    "key_scale": "'tonal'->>'key_scale'",
    "tuning_frequency": "'tonal'->>'tuning_frequency'",
    "tuning_equal_tempered_deviation": "'tonal'->>'tuning_equal_tempered_deviation'",
}

LOWLEVEL_FEATURES_LOWLEVEL = {
    "average_loudness": "'lowlevel'->>'average_loudness'",
    "dynamic_complexity": "'lowlevel'->>'dynamic_complexity'",
    "mfcc_zero_mean": "'lowlevel'->'mfcc'->'mean'->>0",
}

LOWLEVEL_FEATURES_RHYTHM = {
    "bpm": "'rhythm'->>'bpm'",
    "bpm_histogram_first_peak_bpm_mean": "'rhythm'->'bpm_histogram_first_peak_bpm'->>'mean'",
    "bpm_histogram_first_peak_bpm_median": "'rhythm'->'bpm_histogram_first_peak_bpm'->>'median'",
    "bpm_histogram_second_peak_bpm_mean": "'rhythm'->'bpm_histogram_second_peak_bpm'->>'mean'",
    "bpm_histogram_second_peak_bpm_median": "'rhythm'->'bpm_histogram_second_peak_bpm'->>'median'",
    "danceability": "'rhythm'->>'danceability'",
    "onset_rate": "'rhythm'->>'onset_rate'",
}

def _copy_table_into_multiple_files(cursor, table_name, query, rows_per_file, tar, archive_name):
    """Copies data from a table into multiple files and add them to the archive

    Args:
        cursor: a psycopg2 cursor
        table_name: the name of the table to be copied.
        query: the select query for getting data from the table, with appropriate LIMIT and OFFSET parameters.
        rows_per_file: how many rows from query to add to a single file
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
        file_name = "{table_name}-{file_number}".format(table_name=table_name, file_number=file_count)
        path = os.path.join(location, table_name, file_name)
        with open(path, "a") as f:
            logging.info(" - Copying table {table_name} to {file_name}...".format(table_name=table_name, file_name=file_name))
            current_query = query.format(limit=rows_per_file, offset=offset)
            copy_query = "COPY ({query}) TO STDOUT".format(query=current_query)
            cursor.copy_expert(copy_query, f)
            offset += rows_per_file
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
        copy_query = 'COPY ({query}) TO STDOUT'.format(query=query)
        cursor.copy_expert(copy_query, f)

def _add_file_to_tar_and_delete(location, archive_name, tar, filename):
    """Add a file in `location` to an open TarFile at location `archive_name` and then
    delete the file from disk."""
    logging.info(" - adding archive {filename} to tar".format(filename=filename))
    tar.add(os.path.join(location, filename),
            arcname=os.path.join(archive_name, "abdump", filename))
    os.remove(os.path.join(location, filename))

def _copy_dataset_tables(location, tar, archive_name, start_time=None, end_time=None):
    """ Copy datasets tables into separate files within a specified location (directory).
    """
    connection = db.engine.raw_connection()
    try:
        cursor = connection.cursor()
        # dataset
        _copy_table(cursor, location, "dataset", "SELECT %s FROM dataset" %
                    (", ".join(_DATASET_TABLES["dataset"])))
        _add_file_to_tar_and_delete(location, archive_name, tar, "dataset")

        # dataset_class
        _copy_table(cursor, location, "dataset_class", "SELECT %s FROM dataset_class" %
                    (", ".join(_DATASET_TABLES["dataset_class"])))
        _add_file_to_tar_and_delete(location, archive_name, tar, "dataset_class")

        # dataset_class_member
        _copy_table(cursor, location, "dataset_class_member", "SELECT %s FROM dataset_class_member" %
                    (", ".join(_DATASET_TABLES["dataset_class_member"])))
        _add_file_to_tar_and_delete(location, archive_name, tar, "dataset_class_member")

        # dataset_snapshot
        _copy_table(cursor, location, "dataset_snapshot", "SELECT %s FROM dataset_snapshot" %
                    (", ".join(_DATASET_TABLES["dataset_snapshot"])))
        _add_file_to_tar_and_delete(location, archive_name, tar, "dataset_snapshot")

        # dataset_eval_sets
        _copy_table(cursor, location, "dataset_eval_sets", "SELECT %s FROM dataset_eval_sets" %
                    (", ".join(_DATASET_TABLES["dataset_eval_sets"])))
        _add_file_to_tar_and_delete(location, archive_name, tar, "dataset_eval_sets")

        # dataset_eval_jobs
        _copy_table(cursor, location, "dataset_eval_jobs", "SELECT %s FROM dataset_eval_jobs" %
                    (", ".join(_DATASET_TABLES["dataset_eval_jobs"])))
        _add_file_to_tar_and_delete(location, archive_name, tar, "dataset_eval_jobs")

        # challenge
        _copy_table(cursor, location, "challenge", "SELECT %s FROM challenge" %
                    (", ".join(_DATASET_TABLES["challenge"])))
        _add_file_to_tar_and_delete(location, archive_name, tar, "challenge")

        # dataset_eval_challenge
        _copy_table(cursor, location, "dataset_eval_challenge", "SELECT %s FROM dataset_eval_challenge" %
                    (", ".join(_DATASET_TABLES["dataset_eval_challenge"])))
        _add_file_to_tar_and_delete(location, archive_name, tar, "dataset_eval_challenge")
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
        _add_file_to_tar_and_delete(location, archive_name, tar, "version")

        # lowlevel
        _copy_table(cursor, location, "lowlevel", "SELECT %s FROM lowlevel %s" %
                    (", ".join(_TABLES["lowlevel"]), generate_where("submitted")))
        _add_file_to_tar_and_delete(location, archive_name, tar, "lowlevel")

        # lowlevel_json
        query = "SELECT %s FROM lowlevel_json WHERE id IN (SELECT id FROM lowlevel %s) ORDER BY id LIMIT {limit} OFFSET {offset}" \
                % (", ".join(_TABLES["lowlevel_json"]), generate_where("submitted"))
        _copy_table_into_multiple_files(cursor, "lowlevel_json", query, ROWS_PER_FILE, tar, archive_name)

        # model
        query = "SELECT %s FROM model %s" \
                % (", ".join(_TABLES["model"]), generate_where("date"))
        _copy_table(cursor, location, "model", query)
        _add_file_to_tar_and_delete(location, archive_name, tar, "model")

        # highlevel
        _copy_table(cursor, location, "highlevel", "SELECT %s FROM highlevel %s" %
                    (", ".join(_TABLES["highlevel"]), generate_where("submitted")))
        _add_file_to_tar_and_delete(location, archive_name, tar, "highlevel")

        # highlevel_meta
        query = "SELECT %s FROM highlevel_meta WHERE id IN (SELECT id FROM highlevel %s)" \
                % (", ".join(_TABLES["highlevel_meta"]), generate_where("submitted"))
        _copy_table(cursor, location, "highlevel_meta", query)
        _add_file_to_tar_and_delete(location, archive_name, tar, "highlevel_meta")

        # highlevel_model
        # These rows are quite small and there are lots of them, so add 10x as many lines as the lowlevel_json table
        query = "SELECT %s FROM highlevel_model WHERE highlevel IN (SELECT id FROM highlevel %s) ORDER BY id LIMIT {limit} OFFSET {offset}" \
                % (", ".join(_TABLES["highlevel_model"]), generate_where("submitted"))
        _copy_table_into_multiple_files(cursor, "highlevel_model", query, ROWS_PER_FILE * 10, tar, archive_name)

        # statistics
        _copy_table(cursor, location, "statistics", "SELECT %s FROM statistics %s" %
                    (", ".join(_TABLES["statistics"]), generate_where("collected")))
        _add_file_to_tar_and_delete(location, archive_name, tar, "statistics")

        # data_dump
        _copy_table(cursor, location, "data_dump", "(SELECT %s FROM data_dump %s)" %
                    (", ".join(_TABLES["data_dump"]), generate_where("created")))
        _add_file_to_tar_and_delete(location, archive_name, tar, "data_dump")
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


def import_db_dump(archive_path, tables):
    """Import data from .tar.zst archive into the database."""
    zstd_command = ["zstd", "--decompress", "--stdout", archive_path]
    zstd = subprocess.Popen(zstd_command, stdout=subprocess.PIPE)

    table_names = tables.keys()
    latest_file_num_imported = {}
    connection = db.engine.raw_connection()
    try:
        cursor = connection.cursor()

        with tarfile.open(fileobj=zstd.stdout, mode="r|") as tar:
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
                    if member.isfile() and _is_partitioned_table_dump_file(file_name):
                        archive_name, _, table_name, file_name = member.name.split("/")
                        file_num = int(file_name.split("-")[-1])
                        assert(table_name not in latest_file_num_imported or latest_file_num_imported[table_name] < file_num)
                        latest_file_num_imported[table_name] = file_num
                        logging.info(" - Importing data from file %s into %s table..." % (file_name, table_name))
                        cursor.copy_from(tar.extractfile(member), table_name,
                                         columns=_TABLES[table_name])

                    elif file_name in table_names:
                        logging.info(" - Importing data into %s table..." % file_name)
                        cursor.copy_from(tar.extractfile(member), file_name,
                                         columns=tables[file_name])
        connection.commit()
    finally:
        connection.close()

    zstd.stdout.close()
    zstd.wait()

    logging.info('Updating sequences...')
    update_sequences()
    logging.info('Done!')


def dump_lowlevel_features(location, feature_type):
    """Create a CSV dump with selected low level data.

        Args:
        location: Directory where archive will be created.
        feature_type: The type of features to dump (one of tonal, lowlevel, or rhythm)

    Returns:
        Path to created low level CSV dump.
    """

    feature_list = {
        "tonal": LOWLEVEL_FEATURES_TONAL,
        "lowlevel": LOWLEVEL_FEATURES_LOWLEVEL,
        "rhythm": LOWLEVEL_FEATURES_RHYTHM
    }
    if feature_type not in feature_list:
        print("Unknown feature type")
        return
    else:
        features = feature_list[feature_type]

    archive_dirname = "acousticbrainz-lowlevel-features-%s" % (datetime.today().strftime("%Y%m%d"),)
    dump_path = os.path.join(location, archive_dirname)
    utils.path.create_path(dump_path)

    total_dumped = 0
    with db.engine.begin() as connection:
        query = sqlalchemy.text("""
            SELECT id
              FROM lowlevel ll
          ORDER BY submitted""")
        ll_ids = connection.execute(query)

        dump_done = False
        fieldnames = ["mbid", "submission_offset"] + list(features.keys())
        file_name = archive_dirname + "-" + feature_type
        file_path = os.path.join(dump_path, "%s.tar.zst" % file_name)
        with open(file_path, "w") as archive:
            zstd_command = ["zstd", "--compress", "-10"]
            zstd = subprocess.Popen(zstd_command, stdin=subprocess.PIPE, stdout=archive)

            with tarfile.open(fileobj=zstd.stdin, mode="w|") as tar:
                temp_dir = tempfile.mkdtemp()
                with open(os.path.join(temp_dir, "features.csv"), "w") as fp:
                    writer = csv.DictWriter(fp, fieldnames=fieldnames)
                    writer.writeheader()
                    while not dump_done:
                        id_list = ll_ids.fetchmany(size=DUMP_CHUNK_SIZE)
                        if not id_list:
                            dump_done = True
                            break
                        id_list = tuple([i['id'] for i in id_list])

                        features_select = ', '.join(['llj.data->%s AS "%s"' % (path, alias) for alias, path in features.items()])

                        data = connection.execute(sqlalchemy.text("""
                            SELECT gid::text as mbid
                                , submission_offset
                                , %s
                            FROM lowlevel ll
                            JOIN lowlevel_json llj
                                ON ll.id = llj.id
                            WHERE ll.id IN :id_list
                            """ % features_select), {
                                'id_list': id_list,
                            })

                        for row in data:
                            d = dict(row)
                            writer.writerow(d)
                            total_dumped += 1
                tar.add(os.path.join(temp_dir, "features.csv"),
                        arcname=os.path.join(archive_dirname, file_name + ".csv"))

                tar.add(DUMP_LICENSE_FILE_PATH,
                        arcname=os.path.join(archive_dirname, "COPYING"))

            zstd.stdin.close()
            zstd.wait()

    logging.info("Dumped a total of %d recordings" % (total_dumped,))
    return dump_path


def dump_lowlevel_json(location, threads=None, sample=False, num_files_per_archive=float("inf")):
    """Create JSON dump with low level data.

    Args:
        location: Directory where archive will be created.
        threads: Number of threads to use for zstd compression
        sample: if True, generate a sample dump
        num_files_per_archive: The maximum number of recordings to dump in one file.
                   Infinite if not specified.

    Returns:
        Path to created low level JSON dump.
    """

    archive_type = "lowlevel"
    if sample:
        archive_type += "-sample"
    archive_dirname = "acousticbrainz-%s-json-%s" % (archive_type, datetime.today().strftime("%Y%m%d"))
    filename_pattern = archive_dirname + "-%d"

    dump_path = os.path.join(location, archive_dirname)
    utils.path.create_path(dump_path)

    file_num = 0
    with db.engine.begin() as connection:
        query_args = {}
        limit = ""
        if sample:
            query_args = {"limit": SAMPLE_DATASET_SIZE}
            limit = " LIMIT :limit"
        query = sqlalchemy.text("""
            SELECT id
              FROM lowlevel ll
          ORDER BY submitted""" + limit)
        ll_ids = connection.execute(query, query_args)

        data = None
        total_dumped = 0
        dump_done = False
        while True:
            # create a new file and dump recordings there
            filename = filename_pattern % file_num
            file_path = os.path.join(dump_path, "%s.tar.zst" % filename)
            with open(file_path, "w") as archive:
                # Manual testing shows that -10 compression level gives a good tradeoff between
                # compression speed and final file size with AB data
                zstd_command = ["zstd", "--compress", "-10"]
                if threads:
                    zstd_command.append("-T%s" % threads)
                zstd = subprocess.Popen(zstd_command, stdin=subprocess.PIPE, stdout=archive)

                # Creating the archive
                with tarfile.open(fileobj=zstd.stdin, mode="w|") as tar:
                    temp_dir = tempfile.mkdtemp()
                    dumped_count = 0
                    while dumped_count < num_files_per_archive:
                        if data is None:
                            id_list = ll_ids.fetchmany(size=DUMP_CHUNK_SIZE)
                            if not id_list:
                                dump_done = True
                                break
                            id_list = tuple([i['id'] for i in id_list])

                            data = connection.execute(sqlalchemy.text("""
                                SELECT gid::text
                                    , submission_offset
                                    , llj.data::text
                                FROM lowlevel ll
                                JOIN lowlevel_json llj
                                    ON ll.id = llj.id
                                WHERE ll.id IN :id_list
                                """), {
                                    'id_list': id_list,
                                })

                        while dumped_count < num_files_per_archive:
                            row = data.fetchone()
                            if not row:
                                data = None
                                break
                            mbid, submission_offset, json_data = row

                            json_filename = mbid + "-%d.json" % submission_offset
                            dump_tempfile = os.path.join(temp_dir, json_filename)
                            with open(dump_tempfile, "w") as f:
                                f.write(json_data)
                            # Use archive_dirname here (i.e. acousticbrainz-lowlevel-json-20220616) without a -n part suffix
                            # so that uncompressing multiple parts of the same dump will go into the same place
                            tar.add(dump_tempfile, arcname=os.path.join(
                                archive_dirname, "lowlevel", mbid[0:2], mbid[2:3], json_filename))
                            os.unlink(dump_tempfile)

                            dumped_count += 1

                    # Copying legal text
                    tar.add(DUMP_LICENSE_FILE_PATH,
                            arcname=os.path.join(archive_dirname, "COPYING"))

                    shutil.rmtree(temp_dir)  # Cleanup

                    logging.info("Dumped %s recordings in file number %d." % (dumped_count, file_num))
                    file_num += 1
                    total_dumped += dumped_count

                zstd.stdin.close()
                zstd.wait()

                if dump_done:
                    break

    logging.info("Dumped a total of %d recordings in %d files." % (total_dumped, file_num))
    return dump_path


def dump_highlevel_json(location, threads=None, sample=False, num_files_per_archive=float("inf")):
    """Create JSON dump with high-level data.

    Args:
        location: Directory where archive will be created.
        threads: Number of threads to use for zstd compression
        sample: if True, generate a sample dump
        num_files_per_archive: The maximum number of recordings to dump in one file.
                   Infinite if not specified.

    Returns:
        Path to created high-level JSON dump.
    """

    archive_type = "highlevel"
    if sample:
        archive_type += "-sample"
    archive_dirname = "acousticbrainz-%s-json-%s" % (archive_type, datetime.today().strftime("%Y%m%d"))
    filename_pattern = archive_dirname + "-%d"

    dump_path = os.path.join(location, archive_dirname)
    utils.path.create_path(dump_path)
    
    file_num = 0
    with db.engine.begin() as connection:
        query_args = {}
        limit = ""
        if sample:
            query_args = {"limit": SAMPLE_DATASET_SIZE}
            limit = " LIMIT :limit"
        query = sqlalchemy.text("""
            SELECT id
              FROM lowlevel ll
          ORDER BY submitted""" + limit)
        ll_ids = connection.execute(query, query_args)


        total_dumped = 0
        dump_done = False
        while True:
            # create a new file and dump recordings there
            filename = filename_pattern % file_num
            file_path = os.path.join(dump_path, "%s.tar.zst" % filename)
            with open(file_path, "w") as archive:
                # Manual testing shows that -10 compression level gives a good tradeoff between
                # compression speed and final file size with AB data
                zstd_command = ["zstd", "--compress", "-10"]
                if threads:
                    zstd_command.append("-T%s" % threads)
                zstd = subprocess.Popen(zstd_command, stdin=subprocess.PIPE, stdout=archive)

                # Creating the archive
                with tarfile.open(fileobj=zstd.stdin, mode="w|") as tar:
                    temp_dir = tempfile.mkdtemp()
                    dumped_count = 0

                    # Note that in the case that DUMP_CHUNK_SIZE isn't an even multiple of num_files_per_archive,
                    # the dump will have the next multiple of chunk size items, not exactly num_files_per_archive items.
                    while dumped_count < num_files_per_archive:
                        data_list = ll_ids.fetchmany(size=DUMP_CHUNK_SIZE)
                        if not data_list:
                            dump_done = True
                            break

                        metadata_result = connection.execute(sqlalchemy.text("""
                            SELECT ll.submission_offset
                                , hl.id AS id
                                , hl.mbid AS mbid
                                , hlm.data AS metadata
                            FROM highlevel hl
                        LEFT JOIN highlevel_meta hlm
                                ON hl.id = hlm.id
                        LEFT JOIN lowlevel ll
                                ON hl.id = ll.id
                            WHERE hl.id IN :ids
                        """), {
                                'ids': tuple(i['id'] for i in data_list)
                            })
                        metadata = {}
                        for row in metadata_result:
                            submission_offset = row['submission_offset']
                            mbid = str(row['mbid'])
                            hlid = row['id']
                            metadata[hlid] = row

                        # get data for the all the hlids in the current chunk
                        data_result = connection.execute(sqlalchemy.text("""
                                SELECT m.model AS model
                                    , hlmo.data AS model_data
                                    , version.data AS version
                                    , hlmo.highlevel AS id
                                FROM highlevel_model hlmo
                                JOIN model m
                                    ON m.id = hlmo.model
                                JOIN version
                                    ON version.id = hlmo.version
                                WHERE hlmo.highlevel IN :ids
                            """), {
                                'ids': tuple(i['id'] for i in data_list)
                            })


                        # consolidate the different models for each hlid into dicts
                        highlevel_models = defaultdict(dict)
                        for row in data_result.fetchall():
                            model, model_data, version, hlid = row['model'], row['model_data'], row['version'], row['id']
                            model_data['version'] = version
                            highlevel_models[hlid][model] = model_data

                        # create final json for each hlid and dump it
                        for row in metadata.values():
                            submission_offset = row['submission_offset']
                            mbid = str(row['mbid'])
                            hlid = row['id']
                            hl_data = {
                                'metadata': row['metadata'],
                                'highlevel': highlevel_models[hlid],
                            }

                            json_filename = '{mbid}-{no}.json'.format(mbid=mbid, no=submission_offset)
                            dump_tempfile = os.path.join(temp_dir, json_filename)
                            with open(dump_tempfile, "w") as f:
                                f.write(ujson.dumps(hl_data, sort_keys=True))
                            tar.add(dump_tempfile, arcname=os.path.join(
                                archive_dirname, "highlevel", mbid[0:2], mbid[2:3], json_filename))
                            os.unlink(dump_tempfile)

                            dumped_count += 1
                    # Copying legal text
                    tar.add(DUMP_LICENSE_FILE_PATH,
                            arcname=os.path.join(archive_dirname, "COPYING"))

                    shutil.rmtree(temp_dir)  # Cleanup

                    logging.info("Dumped %s recordings." % dumped_count)
                    file_num += 1
                    total_dumped += dumped_count

                if dump_done:
                    break

    logging.info("Dumped a total of %d recordings in %d files." % (total_dumped, file_num))
    return dump_path


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
    dump_type = "full" if full else "partial"
    with db.engine.connect() as connection:
        result = connection.execute(text("""
            INSERT INTO data_dump (created, dump_type)
                 VALUES (now(), :dump_type)
              RETURNING id, created
            """), {
                "dump_type": dump_type,
            })
        row = result.fetchone()
    logging.info("Created new %s dump record (ID: %s)." % (dump_type, row[0]))
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


def _dump_tables(archive_path, threads, copy_tables_method, time_now, start_t=None, end_t=None):
    """Copies the metadata and the tables to the archive.

    Args:
        archive_path (str): Complete path of the archive that will be created.
        threads (int): Maximal number of threads to run during compression.
        copy_tables_method (function): The function to use to create a dump of tables.
        time_now (datetime): Current time.
        start_t (datetime): Start time of the frame that will be used for data selection. (in incremental dumps)
        end_t (datetime): End time of the frame that will be used for data selection.
    """
    archive_name = os.path.basename(archive_path).split('.')[0]
    with open(archive_path, "w") as archive:

        zstd_command = ["zstd", "--compress"]
        if threads is not None:
            zstd_command.append("-T%s" % threads)
        zstd = subprocess.Popen(zstd_command, stdin=subprocess.PIPE, stdout=archive)

        # Creating the archive
        with tarfile.open(fileobj=zstd.stdin, mode="w|") as tar:
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
            copy_tables_method(archive_tables_dir, tar, archive_name, start_t, end_t)

            shutil.rmtree(temp_dir)

        zstd.stdin.close()
        zstd.wait()


def dump_dataset_tables(location, threads=None):
    """Create full dump of dataset tables in a specified location.

    Args:
        location: Directory where archive will be created.
        threads: Maximum number of threads to run during compression
    Returns:
        Path to created dump.
    """
    utils.path.create_path(location)
    time_now = datetime.today()
    archive_name = "acousticbrainz-dataset-dump-%s" % time_now.strftime("%Y%m%d-%H%M%S")

    archive_path = os.path.join(location, archive_name + ".tar.zst")
    _dump_tables(
        archive_path=archive_path,
        threads=threads,
        copy_tables_method=_copy_dataset_tables,
        time_now=time_now,
    )
    return archive_path


def dump_public_tables(location, threads=None, full=True, dump_id=None):
    """Create full dump of public data tables in a specified location.

    Args:
        location: Directory where archive will be created.
        threads: Maximum number of threads to run during compression
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

    time_now = datetime.today()

    archive_path = os.path.join(location, archive_name + ".tar.zst")
    _dump_tables(
        archive_path=archive_path,
        threads=threads,
        copy_tables_method=_copy_tables,
        time_now=time_now,
    )
    return archive_path


def import_dump(archive_path):
    """Imports a database dump from .tar.zst archive into the database."""
    import_db_dump(archive_path, _TABLES)


def import_datasets_dump(archive_path):
    """Import datasets from .tar.zst archive into the database."""
    import_db_dump(archive_path, _DATASET_TABLES)
