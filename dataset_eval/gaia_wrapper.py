"""
This module provides wrapper functions for functionality in the Gaia
library (Python bindings), which is a main part of the dataset evaluator.

More info about Gaia is available at https://github.com/MTG/gaia.
"""
from gaia2.scripts.classification.generate_classification_project \
    import generateProject as generate_classification_project
from gaia2.scripts.classification.run_tests import runTests as run_tests
from gaia2.scripts.classification.get_classification_results import ClassificationResults
from gaia2.scripts.classification.generate_svm_history_from_config import trainSVM as train_svm
from gaia2.classification import ConfusionMatrix, GroundTruth
from gaia2.fastyaml import yaml
from gaia2 import DataSet, transform

import os
import os.path


PROJECT_FILE_NAME = "project.yaml"


def train_model(project_dir, groundtruth_file, filelist_file):
    """Trains best model for classification based on provided dataset.

    Args:
        project_dir: Path to working directory for the evaluation project. This
            directory needs to include the project file named `project.yaml`.
        groundtruth_file: Path to the groundtruth file in YAML format that
            contains info about contents of each class in the dataset.
        filelist_file: Path to the filelist in YAML format that contains
            mappings between all items (recordings) in the dataset and files
            that contain low-level info about these items.

    Returns:
        Dictionary that contains information about best model for the dataset.
        See `select_best_model` function for more info.
    """
    project_file = os.path.join(project_dir, PROJECT_FILE_NAME)
    generate_classification_project(
        project_file=project_file,
        groundtruth_file=groundtruth_file,
        filelist_file=filelist_file,
        datasets_dir=os.path.join(project_dir, "datasets"),
        results_dir=os.path.join(project_dir, "results"),
    )
    run_tests(project_file)
    return select_best_model(project_dir)


def select_best_model(project_dir):
    """Selects most accurate classifier parameters for the specified project.

    Args:
        project_file_path: Path to the project file in YAML format.

    Returns:
        Dictionary that contains information about best model for the dataset:
            - parameters: classifier parameters for selected model;
            - accuracy: accuracy of selected model;
            - confusion_matrix: simplified version of confusion matrix for
                selected model.
            - history_path: path to the history file generated using returned
                set of parameters for the best model.
    """
    with open(os.path.join(project_dir, PROJECT_FILE_NAME)) as project_file:
        project = yaml.load(project_file)

    classifierName = project["className"]
    results = ClassificationResults()
    results.readResults(project["resultsDirectory"])
    best_accuracy, best_result_file, best_params = results.best(1, None)[0]

    cm = ConfusionMatrix()
    cm.load(best_result_file)
    simplified_cm = {}
    for key, val in cm.matrix.items():
        simplified_cm[key] = {}
        for predicted_key, predicted_val in val.items():
            simplified_cm[key][predicted_key] = len(predicted_val)

    history_file_path = os.path.join(project_dir, "%s.history" % classifierName)
    train_svm_history(project, best_params, history_file_path)

    return {
        "parameters": best_params,
        "accuracy": round(best_accuracy, 2),
        "confusion_matrix": simplified_cm,
        "history_path": history_file_path,
    }


def train_svm_history(project, params, output_file_path):
    params_model = params["model"]
    if params_model.pop("classifier") != "svm":
        raise GaiaWrapperException("Can only use this script on SVM config parameters.")

    ds = DataSet()
    ds.load(os.path.join(
        project["datasetsDirectory"],
        "%s-%s.db" % (project["className"], params_model.pop("preprocessing"))
    ))

    gt = GroundTruth.fromFile(project["groundtruth"])
    gt.className = "highlevel." + project["className"]

    history = train_svm(ds, gt, **params_model)  # doing the whole training
    if isinstance(output_file_path, unicode):
        output_file_path = output_file_path.encode("utf-8")
    history.save(output_file_path)


class GaiaWrapperException(Exception):
    pass
