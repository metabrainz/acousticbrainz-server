from __future__ import print_function

import sys
import os
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), ".."))
import config

from dataset_eval import gaia_wrapper
from dataset_eval import artistfilter
import gaia2.fastyaml as yaml
import db
import db.data
import db.dataset
import db.dataset_eval
import db.exceptions
import utils.path
import tempfile
import logging
import shutil
import time
import json
import os

SLEEP_DURATION = 30  # number of seconds to wait between runs
HISTORY_STORAGE_DIR = os.path.join(config.FILE_STORAGE_DIR, "history")


def main():
    logging.info("Starting dataset evaluator...")
    while True:
        db.init_db_engine(config.SQLALCHEMY_DATABASE_URI)
        pending_job = db.dataset_eval.get_next_pending_job()
        if pending_job:
            logging.info("Processing job %s..." % pending_job["id"])
            evaluate_dataset(pending_job)
        else:
            logging.info("No pending datasets. Sleeping %s seconds." % SLEEP_DURATION)
            time.sleep(SLEEP_DURATION)


def evaluate_dataset(eval_job):
    db.dataset_eval.set_job_status(eval_job["id"], db.dataset_eval.STATUS_RUNNING)

    temp_dir = tempfile.mkdtemp()

    try:
        dataset = db.dataset.get_snapshot(eval_job["snapshot_id"])

        train, test = artistfilter.filter(eval_job["snapshot_id"], eval_job["options"])
        db.dataset_eval.add_sets_to_job(eval_job["id"], train, test)

        logging.info("Generating filelist.yaml and copying low-level data for evaluation...")
        filelist_path = os.path.join(temp_dir, "filelist.yaml")
        filelist = dump_lowlevel_data(train.keys(), os.path.join(temp_dir, "data"))
        with open(filelist_path, "w") as f:
            yaml.dump(filelist, f)

        logging.info("Generating groundtruth.yaml...")
        groundtruth_path = os.path.join(temp_dir, "groundtruth.yaml")
        with open(groundtruth_path, "w") as f:
            yaml.dump(create_groundtruth_dict(dataset["name"], train), f)

        logging.info("Training model...")
        results = gaia_wrapper.train_model(
            groundtruth_file=groundtruth_path,
            filelist_file=filelist_path,
            project_dir=temp_dir,
        )
        logging.info("Saving results...")
        save_history_file(results["history_path"], eval_job["id"])
        db.dataset_eval.set_job_result(eval_job["id"], json.dumps({
            "parameters": results["parameters"],
            "accuracy": results["accuracy"],
            "confusion_matrix": results["confusion_matrix"],
            "history_path": results["history_path"],
        }))
        db.dataset_eval.set_job_status(eval_job["id"], db.dataset_eval.STATUS_DONE)
        logging.info("Evaluation job %s has been completed." % eval_job["id"])

    # TODO(roman): Also need to catch exceptions from Gaia.
    except db.exceptions.DatabaseException as e:
        logging.info("Evaluation job %s has failed!" % eval_job["id"])
        db.dataset_eval.set_job_status(
            job_id=eval_job["id"],
            status=db.dataset_eval.STATUS_FAILED,
            status_msg=str(e),
        )
        logging.info(e)

    finally:
        shutil.rmtree(temp_dir)  # Cleanup


def create_groundtruth_dict(name, datadict):
    groundtruth = {
        "type": "unknown",  # TODO: See if that needs to be modified.
        "version": 1.0,
        "className": db.dataset._slugify(unicode(name)),
        "groundTruth": {},
    }
    for r, cls in datadict.items():
        if isinstance(r, unicode):
            r = r.encode("UTF-8")
        groundtruth["groundTruth"][r] = cls.encode("UTF-8")

    return groundtruth


def create_groundtruth(dataset):
    groundtruth = {
        "type": "unknown",  # TODO: See if that needs to be modified.
        "version": 1.0,
        "className": db.dataset._slugify(unicode(dataset["name"])),
        "groundTruth": {},
    }
    for cls in dataset["classes"]:
        for recording_mbid in cls["recordings"]:
            groundtruth["groundTruth"][recording_mbid] = cls["name"].encode("UTF-8")
    return groundtruth


def dump_lowlevel_data(recordings, location):
    """Dumps low-level data for all recordings into specified location.

    Args:
        recordings: List of MBIDs of recordings.
        location: Path to directory where low-level data will be saved.

    Returns:
        Filelist.
    """
    utils.path.create_path(location)
    filelist = {}
    for recording in recordings:
        filelist[recording] = os.path.join(location, "%s.yaml" % recording)
        with open(filelist[recording], "w") as f:
            f.write(lowlevel_data_to_yaml(db.data.load_low_level(recording)))
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
    if 'lossless' in data['metadata']['audio_properties']:
        del data['metadata']['audio_properties']['lossless']

    return yaml.dump(data)


def extract_recordings(dataset):
    """Extracts set of recordings used in a dataset."""
    recordings = set()
    for cls in dataset["classes"]:
        for recording_mbid in cls["recordings"]:
            recordings.add(recording_mbid)
    return recordings


def save_history_file(history_file_path, job_id):
    directory = os.path.join(HISTORY_STORAGE_DIR, job_id[0:1], job_id[0:2])
    utils.path.create_path(directory)
    destination = os.path.join(directory, job_id)
    shutil.copyfile(history_file_path, destination)
    return destination


if __name__ == "__main__":
    main()
