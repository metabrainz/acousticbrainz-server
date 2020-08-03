import os
import argparse
from ..helper_functions.utils import load_yaml
import time
from ..transformation.load_ground_truth import ListGroundTruthFiles
from ..classification.train_class import train_class


def create_classification_project(ground_truth_directory, project_file=None, exports_directory=None, exports_path=None,
                                  seed=None, jobs=-1, verbose=1, logging="logging.INFO"):
    """
    Args:
        ground_truth_directory: The path (str) to the dataset directory where the
         groundtruth yaml file is located. It is required.
        project_file: The name (str) of the project configuration yaml file that
            will be created. Default: None. If None, the tool will create
            automatically a project file name in form of "project_CLASS_NAME",
            where CLASS_NAME is the target class as referred to the groundtruth data.
        exports_directory: The name (str) of the directory that the results
            of the classification project will be save to. Default: None. If None,
            the tool will automatically create a directory with the name
            "exports_CLASS_NAME", where CLASS_NAME is the target class as referred
            to the groundtruth data.
        exports_path: The path (str) to the exports directory. Default: None. If
            None, the exports directory will be saved inside the app folder.
        seed: The seed (int) of the random shuffle generator. Default: 1
        jobs: The cores (int) that will be exploited during the training phase.
            Default: -1. If -1, all the available cores will be used.
        verbose: The verbosity (int) of the printed messages where this function
            is available (for example in sklearn's GridSearch algorithm). Default: 1.
            The higher the number the higher the verbosity.
        logging: The level (str) of the logging prints. Default: "logging.INFO".
            Available values: logging.DEBUG, logging.INFO, logging.WARNING,
            logging.ERROR, logging.CRITICAL.
    """
    try:
        path_template = os.path.dirname(os.path.realpath(__file__))
        project_template = load_yaml(path_template, "configuration_template.yaml")
    except Exception as e:
        print('Unable to open project configuration template:', e)
        raise

    print("-------------------------------------------------------")
    print()
    if seed is None:
        seed = time.time()

    print("Seed argument: {}".format(seed))

    project_template["ground_truth_directory"] = ground_truth_directory
    project_template["project_file"] = project_file
    project_template["logging_level"] = logging
    project_template["seed"] = seed
    project_template["parallel_jobs"] = jobs
    project_template["verbose"] = verbose

    # if empty, path is declared as the app's main directory
    if exports_path is None:
        exports_path = os.getcwd()

    print("Exports path: {}".format(exports_path))
    project_template["exports_path"] = exports_path

    print("Exports directory: {}".format(exports_directory))

    print()
    print()
    print("-------------------------------------------------------")
    # print("AFTER:")
    # pprint(project_template)

    gt_files_list = ListGroundTruthFiles(project_template).list_gt_filenames()
    print("List GroundTruth yaml files found:")
    print(gt_files_list)
    print("LOAD GROUND TRUTH")
    for gt_file in gt_files_list:
        train_class(project_template, gt_file, exports_directory, logging)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Generates a project configuration file given a filelist, a groundtruth file, '
                    'and the directories to store the datasets and the results files. '
                    'The script has a parameter to specify the project template to use. '
                    'If it is not specified, it will try to guess the appropriated one from the '
                    'essentia version found on the descriptor files.')

    parser.add_argument("-g", "--groundtruth",
                        dest="ground_truth_directory",
                        default="datasets",
                        help="Path of the main dataset directory containing the groundtruth file/s.",
                        required=True)

    parser.add_argument("-f", "--file",
                        dest="project_file",
                        help="Name of the project configuration file (.yaml) will be stored. If not specified "
                             "it takes automatically the name <project_CLASS_NAME>.")

    parser.add_argument("-d", "--exportsdir",
                        dest="exports_directory",
                        help="Name of the exports directory that the project's results will be stored.")

    parser.add_argument("-p", "--path",
                        dest="exports_path",
                        help="Path where the project results will be stored. If empty, the results will be saved in "
                             "the main app directory.")

    parser.add_argument("-s", "--seed",
                        default=None,
                        help="Seed is used to generate the random shuffled dataset applied later to folding.",
                        type=int)

    parser.add_argument("-j", "--jobs",
                        default=-1,
                        help="Parallel jobs. Set to -1 to use all the available cores",
                        type=int)

    parser.add_argument("-v", "--verbose",
                        default=1,
                        help="Controls the verbosity: the higher, the more messages.",
                        type=int)

    parser.add_argument("-l", "--logging",
                        default="logging.INFO",
                        help="The logging level that will be printed logging.DEBUG, logging.INFO, logging.WARNING, "
                             "logging.ERROR, logging.CRITICAL).",
                        type=str)

    args = parser.parse_args()

    create_classification_project(ground_truth_directory=args.ground_truth_directory,
                                  project_file=args.project_file,
                                  exports_directory=args.exports_directory,
                                  exports_path=args.exports_path,
                                  seed=args.seed,
                                  jobs=args.jobs,
                                  verbose=args.verbose,
                                  logging=args.logging)
