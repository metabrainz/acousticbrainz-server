from __future__ import print_function

import json
import logging
import os
import shutil
import tempfile
import time

from flask import current_app

import db
import db.data
import db.dataset
import db.dataset_eval
import db.exceptions
import utils.path
import yaml
from dataset_eval import artistfilter

eval_tool_use = "gaia"
is_sklearn = os.getenv("MODEL_TRAINING_SKLEARN")
if is_sklearn == "1":
    from acousticbrainz.models.sklearn.model.classification_project import create_classification_project
    from acousticbrainz.models.sklearn.classification.matrix_creation import simplified_matrix_export
    eval_tool_use = "sklearn"

is_gaia = os.getenv("MODEL_TRAINING_GAIA")
if is_gaia == "1":
    # import gaia2.fastyaml as yaml
    from dataset_eval import gaia_wrapper
    eval_tool_use = "gaia"

SLEEP_DURATION = 30  # number of seconds to wait between runs


def main():
    logging.info("Starting dataset evaluator...")
    dataset_dir = current_app.config["DATASET_DIR"]
    logging.info("Dataset dir path: {}".format(dataset_dir))
    storage_dir = os.path.join(current_app.config["FILE_STORAGE_DIR"], "history")
    logging.info("Storage dir path: {}".format(storage_dir))
    while True:
        pending_job = db.dataset_eval.get_next_pending_job(eval_tool_use)
        if pending_job:
            logging.info("Processing job %s..." % pending_job["id"])
            evaluate_dataset(pending_job, dataset_dir, storage_dir)
        else:
            logging.info("No pending datasets. Sleeping %s seconds." % SLEEP_DURATION)
            time.sleep(SLEEP_DURATION)


def evaluate_dataset(eval_job, dataset_dir, storage_dir):
    db.dataset_eval.set_job_status(eval_job["id"], db.dataset_eval.STATUS_RUNNING)

    eval_location = os.path.join(os.path.abspath(dataset_dir), eval_job["id"])
    utils.path.create_path(eval_location)
    temp_dir = os.path.join(eval_location, 'temp')
    utils.path.create_path(temp_dir)

    training_tool = eval_job["options"].get("training_tool", "gaia")

    try:
        snapshot = db.dataset.get_snapshot(eval_job["snapshot_id"])

        train, test = artistfilter.filter(eval_job["snapshot_id"], eval_job["options"])
        db.dataset_eval.add_sets_to_job(eval_job["id"], train, test)

        if training_tool == "gaia":
            logging.info("Generating filelist.yaml and copying low-level data for evaluation...")
            filelist_path = os.path.join(eval_location, "filelist.yaml")
            filelist = dump_lowlevel_data(train.keys(), temp_dir)
            with open(filelist_path, "w") as f:
                yaml.safe_dump(filelist, f)
        elif training_tool == "sklearn":
            dump_lowlevel_data_sklearn(train.keys(), dataset_dir)

        logging.info("Generating groundtruth.yaml...")
        groundtruth_path = os.path.join(eval_location, "groundtruth.yaml")
        with open(groundtruth_path, "w") as f:
            yaml.safe_dump(create_groundtruth_dict(snapshot["data"]["name"], train), f)

        if training_tool == "gaia":
            logging.info("Training GAIA model...")
            evaluate_gaia(eval_job["options"], eval_location, groundtruth_path, filelist_path, storage_dir, eval_job)
        elif training_tool == "sklearn":
            logging.info("Training SKLEARN model...")
            evaluate_sklearn(options=eval_job["options"],
                             eval_location=eval_location,
                             ground_truth_file=groundtruth_path,
                             dataset_dir=dataset_dir,
                             storage_dir=storage_dir,
                             eval_job=eval_job)

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


def evaluate_gaia(options, eval_location, groundtruth_path, filelist_path, storage_dir, eval_job):
    results = gaia_wrapper.train_model(
        project_dir=eval_location,
        groundtruth_file=groundtruth_path,
        filelist_file=filelist_path,
        c_values=options.get("c_values", []),
        gamma_values=options.get("gamma_values", []),
        preprocessing_values=options.get("preprocessing_values", [])
    )
    logging.info("Saving results...")
    save_history_file(storage_dir, results["history_path"], eval_job["id"])
    db.dataset_eval.set_job_result(eval_job["id"], json.dumps({
        "project_path": eval_location,
        "parameters": results["parameters"],
        "accuracy": results["accuracy"],
        "confusion_matrix": results["confusion_matrix"],
        "history_path": results["history_path"],
    }))


def evaluate_sklearn(options, eval_location, ground_truth_file, dataset_dir, storage_dir, eval_job):
    create_classification_project(ground_truth_file=ground_truth_file,
                                  dataset_dir=dataset_dir,
                                  project_file=eval_job["id"],
                                  exports_path=eval_location,
                                  c_values=options.get("c_values", []),
                                  gamma_values=options.get("gamma_values", []),
                                  preprocessing_values=options.get("preprocessing_values", [])
                                  )

    logging.info("Saving results...")
    results = load_best_results_sklearn(exported_path=eval_location,
                                        project_file=eval_job["id"])
    db.dataset_eval.set_job_result(eval_job["id"], json.dumps({
        "project_path": eval_location,
        "parameters": results["parameters"],
        "accuracy": results["accuracy"],
        "confusion_matrix": results["confusion_matrix"],
        "history_path": results["history_path"],
    }))


def load_best_results_sklearn(exported_path, project_file):
    project_conf_file_path = os.path.join(exported_path, "{}.yaml".format(project_file))
    logging.info("Config file path: {}".format(project_conf_file_path))
    with open(project_conf_file_path) as fp:
        project_data = yaml.load(fp, Loader=yaml.FullLoader)
    logging.info("Model: {}".format(project_data['class_name']))

    # load the best model dictionary
    best_model_path = os.path.join(exported_path, project_file, "best_model_{}.json".format(project_data['class_name']))
    logging.info("Best model path: {}".format(best_model_path))
    with open(best_model_path) as json_file:
        data_best_model = json.load(json_file)

    # load the best model's instances and matrix dictionary
    fold_matrix_path = os.path.join(exported_path, project_file, "folded_dataset_instances_cm.json")
    logging.info("Best Instances and Matrix JSON path: {}".format(fold_matrix_path))
    with open(fold_matrix_path) as json_file_cm:
        data_fold_matrix = json.load(json_file_cm)

    # load the best model's simplified matrix dictionary
    # fold_simplified_matrix_path = os.path.join(exported_path, project_file, "folded_simplified_matrix.json")
    # logging.info(f"Best models simplified matrix JSON path: {fold_simplified_matrix_path}")
    # with open(fold_simplified_matrix_path) as json_file_simple_cm:
    #     data_fold_simplified_matrix = json.load(json_file_simple_cm)

    # export the matrix dictionary from the folded dataset
    simplified_cm = simplified_matrix_export(best_result_file="folded_dataset_results_matrix.json",
                                             logger=logging,
                                             export_save_path=exported_path,
                                             export_name="simplified_cm.json",
                                             write_mode=False)

    return {
        "parameters": data_best_model["params"],
        # for consistency with gaia which reports accuracy on scale of 0 to 100
        "accuracy": round(data_best_model["score"] * 100, 2),
        "confusion_matrix": simplified_cm,
        "history_path": "Does not exist because of sklearn training usage"
    }


def create_groundtruth_dict(name, datadict):
    groundtruth = {
        "type": "unknown",  # TODO: See if that needs to be modified.
        "version": 1.0,
        "className": db.dataset._slugify(name),
        "groundTruth": {},
    }
    for r, cls in datadict.items():
        # if isinstance(r, unicode):
        #     r = r.encode("UTF-8")
        groundtruth["groundTruth"][r] = cls

    return groundtruth


def create_groundtruth(dataset):
    groundtruth = {
        "type": "unknown",  # TODO: See if that needs to be modified.
        "version": 1.0,
        "className": db.dataset._slugify(dataset["name"]),
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

    return yaml.safe_dump(data)


def dump_lowlevel_data_sklearn(recordings, location):
    """Dumps low-level data to JSON for all recordings into specified location.

        Args:
            recordings: List of MBIDs of recordings.
            location: Path to directory where low-level data will be saved.

    """
    utils.path.create_path(location)
    filelist = {}
    for recording in recordings:
        logging.info("Recording: {}".format(recording))
        filelist[recording] = os.path.join(location, "%s.json" % recording)
        logging.info("Recoding path: {}".format(filelist[recording]))
        with open(filelist[recording], 'w') as outfile:
            json.dump(lowlevel_data_cleaning(db.data.load_low_level(recording)), outfile)
    logging.info("JSON data stored successfully.")


def lowlevel_data_cleaning(data):
    """Prepares dictionary with low-level data about recording for processing.
    """
    # Removing descriptors, that will otherwise break gaia_fusion due to
    # incompatibility of layouts (see Gaia implementation for more details).
    if "tags" in data["metadata"]:
        del data["metadata"]["tags"]
    if "sample_rate" in data["metadata"]["audio_properties"]:
        del data["metadata"]["audio_properties"]["sample_rate"]
    if 'lossless' in data['metadata']['audio_properties']:
        del data['metadata']['audio_properties']['lossless']
    # logging.info("Data: {}".format(data))
    return data


def extract_recordings(dataset):
    """Extracts set of recordings used in a dataset."""
    recordings = set()
    for cls in dataset["classes"]:
        for recording_mbid in cls["recordings"]:
            recordings.add(recording_mbid)
    return recordings


def save_history_file(storage_dir, history_file_path, job_id):
    directory = os.path.join(storage_dir, job_id[0:1], job_id[0:2])
    utils.path.create_path(directory)
    destination = os.path.join(directory, "%s.history" % job_id)
    shutil.copyfile(history_file_path, destination)
    return destination
