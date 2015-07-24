from gaia2.scripts.classification.generate_classification_project \
    import generateProject as generate_classification_project
from gaia2.scripts.classification.run_tests import runTests as run_tests
from gaia2.scripts.classification.get_classification_results import ClassificationResults
from gaia2.classification import ConfusionMatrix
from gaia2.fastyaml import yaml

import os
import os.path


def train_model(project_dir, groundtruth_file, filelist_file):
    project_file = os.path.join(project_dir, "project.yaml")
    generate_classification_project(
        project_file=project_file,
        groundtruth_file=groundtruth_file,
        filelist_file=filelist_file,
        datasets_dir=os.path.join(project_dir, "datasets"),
        results_dir=os.path.join(project_dir, "results"),
    )
    run_tests(project_file)
    return select_best_model(project_file)


def select_best_model(project_file_path):
    with open(project_file_path) as project_file:
        project = yaml.load(project_file)

    results = ClassificationResults()
    results.readResults(project["resultsDirectory"])
    best_accuracy, best_result_file, best_params = results.best(1, None)[0]

    cm = ConfusionMatrix()
    cm.load(best_result_file)
    return {
        "parameters": best_params,
        "accuracy": best_accuracy,
        "confusion_matrix": cm.matrix,
    }
