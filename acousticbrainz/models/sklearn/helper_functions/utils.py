import os
import yaml


def load_yaml(path_to_file, file):
    """
    Args:
        path_file:

    Returns:
        The configuration data loaded from the template.
    """
    try:
        with open(os.path.join(path_to_file, file)) as fp:
            config_data = yaml.load(fp, Loader=yaml.FullLoader)
            if isinstance(config_data, dict):
                return config_data
            else:
                return None
    except ImportError:
        print("WARNING: could not import yaml module")
        return None


def create_directory(exports_path, directory):
    # find dynamically the current script directory
    full_path = os.path.join(exports_path, directory)
    # create path directories if not exist --> else return the path
    os.makedirs(full_path, exist_ok=True)
    return full_path


def change_weights_val(i):
    """
    Is is used in the TrainingProcesses class. It is used to transform each value of
    the balanced classes list in the configuration file Grid parameters of the classifier:
        * True --> balanced
        * False --> None
    Args:
        i: The value inserted
    Returns:
        "balanced" in case the value of the list is True, else None if it is set to False.
    """
    if i is True:
        return "balanced"
    elif i is False:
        return None
    return i


def extract_training_processes(config):
    """ Extracts the pre-processing steps that are specified in "List of classifiers
    to be trained" section of the configuration template. These are the amount
    of the prep-processing steps with the relevant training that will be executed.

    Returns:
        A list of the processes that have been identified with the corresponding parameter grid.
    """
    evaluations = config["evaluations"]["nfoldcrossvalidation"]
    print("Evaluations countered: {}".format(len(evaluations)))
    evaluation_counter = 0
    trainings_counted = 0
    processes = []
    for evaluation in evaluations:
        for nfold_number in evaluation["nfold"]:
            classifiers = config["classifiers"]["svm"]
            for classifier in classifiers:
                for pre_processing in classifier["preprocessing"]:
                    for clf_type in classifier["type"]:
                        if clf_type == "C-SVC":
                            process_dict = {
                                "evaluation": evaluation_counter,
                                "classifier": clf_type,
                                "preprocess": pre_processing,
                                "kernel": [i.lower() for i in classifier["kernel"]],  # lowercase the values
                                "C": [2 ** x for x in classifier["C"]],  # 2 ** c
                                "gamma": [2 ** x for x in classifier["gamma"]],  # 2 ** gamma
                                "balance_classes": [change_weights_val(i) for i in classifier["balance_classes"]],
                                "n_fold": nfold_number
                            }
                            # append the pre-processing steps list
                            processes.append(process_dict)
                            # increase counter by 1
                            trainings_counted += 1
        # increase evaluation counter by 1
        evaluation_counter += 1

    print("Trainings to be applied: {}".format(trainings_counted))

    return processes
