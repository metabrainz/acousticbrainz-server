from __future__ import print_function

import sys
import os
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), ".."))
import config

from dataset_eval import gaia_wrapper
import gaia2.fastyaml as yaml
import db
import db.data
import db.dataset
import db.dataset_eval
import db.exceptions
from db.utils import create_path
import unicodedata
import tempfile
import logging
import shutil
import time
import json
import os
import re

SLEEP_DURATION = 30  # number of seconds to wait between runs


def main():
    logging.info("Starting dataset evaluator...")
    while True:
        db.init_db_connection(config.PG_CONNECT)
        pending_job = db.dataset_eval.get_next_pending_job()
        if pending_job:
            logging.info("Processing job %s..." % pending_job["id"])
            evaluate_dataset(pending_job)
        else:
            logging.info("No pending datasets. Sleeping %s seconds." % SLEEP_DURATION)
            db.close_connection()
            time.sleep(SLEEP_DURATION)


def evaluate_dataset(eval_job):
    db.dataset_eval.set_job_status(eval_job["id"], db.dataset_eval.STATUS_RUNNING)
    temp_dir = tempfile.mkdtemp()

    try:
        dataset = db.dataset.get(eval_job["dataset_id"])

        logging.info("Generating filelist.yaml and copying low-level data for evaluation...")
        filelist_path = os.path.join(temp_dir, "filelist.yaml")
        filelist = dump_lowlevel_data(extract_recordings(dataset), os.path.join(temp_dir, "data"))
        with open(filelist_path, "w") as f:
            yaml.dump(filelist, f)

        logging.info("Generating groundtruth.yaml...")
        groundtruth_path = os.path.join(temp_dir, "groundtruth.yaml")
        with open(groundtruth_path, "w") as f:
            yaml.dump(create_groundtruth(dataset), f)

        logging.info("Training model...")
        results = gaia_wrapper.train_model(
            groundtruth_file=groundtruth_path,
            filelist_file=filelist_path,
            project_dir=temp_dir,
        )
        logging.info("Saving results...")
        db.dataset_eval.set_job_result(eval_job["id"], json.dumps(results))
        db.dataset_eval.set_job_status(eval_job["id"], db.dataset_eval.STATUS_DONE)
        logging.info("Evaluation job %s has been completed." % eval_job["id"])

    # TODO(roman): Also need to catch exceptions from Gaia.
    except db.exceptions.DatabaseException as e:
        logging.info("Evaluation job %s has failed!" % eval_job["id"])
        db.dataset_eval.set_job_status(eval_job["id"], db.dataset_eval.STATUS_FAILED,
                                       status_msg=str(e))
        logging.info(e)

    finally:
        shutil.rmtree(temp_dir)  # Cleanup


def create_groundtruth(dataset):
    groundtruth = {
        "type": "unknown",  # TODO: See if that needs to be modified.
        "version": 1.0,
        "className": _slugify(unicode(dataset["name"])),
        "groundTruth": {},
    }
    for cls in dataset["classes"]:
        for recording_mbid in cls["recordings"]:
            groundtruth["groundTruth"][recording_mbid] = cls["name"]
    return groundtruth


def dump_lowlevel_data(recordings, location):
    """Dumps low-level data for all recordings into specified location.

    Args:
        recordings: List of MBIDs of recordings.
        location: Path to directory where low-level data will be saved.

    Returns:
        Filelist.
    """
    create_path(location)
    filelist = {}
    for recording in recordings:
        filelist[recording] = os.path.join(location, "%s.yaml" % recording)
        with open(filelist[recording], "w") as f:
            f.write(lowlevel_data_to_yaml(json.loads(db.data.load_low_level(recording))))
    return filelist


def lowlevel_data_to_yaml(data):
    """Prepares dictionary with low-level data about recording for processing
    and converts it into YAML string.
    """
    # Removing descriptors, that will otherwise break gaia_fusion due to
    # incompatibility of layouts (see Gaia implementation for more details).
    if "tags" in data["metadata"]:
        del data["metadata"]["tags"]
    if "sample_rate" in data["metadata"]["audio_properties"]:
        del data["metadata"]["audio_properties"]["sample_rate"]

    return yaml.dump(data)


def extract_recordings(dataset):
    """Extracts set of recordings used in a dataset."""
    recordings = set()
    for cls in dataset["classes"]:
        for recording_mbid in cls["recordings"]:
            recordings.add(recording_mbid)
    return recordings


def _slugify(string):
    """Converts unicode string to lowercase, removes alphanumerics and
    underscores, and converts spaces to hyphens. Also strips leading and
    trailing whitespace.
    """
    string = unicodedata.normalize('NFKD', string).encode('ascii', 'ignore').decode('ascii')
    string = re.sub('[^\w\s-]', '', string).strip().lower()
    return re.sub('[-\s]+', '-', string)


if __name__ == "__main__":
    main()
