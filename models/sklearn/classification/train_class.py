import os
from termcolor import colored
import yaml

from ..transformation.load_ground_truth import GroundTruthLoad
from ..classification.classification_task_manager import ClassificationTaskManager
from ..transformation.load_ground_truth import DatasetExporter
from ..helper_functions.logging_tool import LoggerSetup


def train_class(config, gt_file, exports_directory, c_values, gamma_values, preprocessing_values, log_level):
    exports_path = config["exports_path"]
    gt_data = GroundTruthLoad(config, gt_file, exports_path, log_level)
    # tracks shuffled and exported
    tracks_listed_shuffled = gt_data.export_gt_tracks()

    # class to train
    class_name = gt_data.export_train_class()
    config["class_name"] = class_name

    # project directory where the models and outputs will be saved
    if exports_directory is None:
        prefix_exports_dir = "exports"
        config["exports_directory"] = "{}_{}".format(prefix_exports_dir, class_name)
    else:
        config["exports_directory"] = exports_directory

    config = update_parameters(config=config,
                               c_values=c_values,
                               gamma_values=gamma_values,
                               preprocessing_values=preprocessing_values)

    logger = LoggerSetup(config=config,
                         exports_path=exports_path,
                         name="train_model_{}".format(class_name),
                         train_class=class_name,
                         mode="w",
                         level=log_level).setup_logger()
    
    logger.info("---- TRAINING FOR THE {} MODEL HAS JUST STARTED ----".format(class_name))

    logger.debug("Type of exported GT data exported: {}".format(type(tracks_listed_shuffled)))

    # name the project file
    if config["project_file"] is None:
        prefix_project_file = "project"
        project_file_name_save = "{}_{}.yaml".format(prefix_project_file, class_name)
    else:
        project_file_name_save = "{}.yaml".format(config["project_file"])
    logger.info("Project yaml file name: {}".format(project_file_name_save))
    # save the project file
    project_file_save_path = os.path.join(exports_path, project_file_name_save)
    with open(os.path.join(project_file_save_path), "w") as template_file:
        template_data_write = yaml.dump(config, template_file)

    print("First N sample of shuffled tracks: \n{}".format(tracks_listed_shuffled[:4]))

    # create the exports with the features DF, labels, and tracks together
    features, labels, tracks = DatasetExporter(config=config,
                                               tracks_list=tracks_listed_shuffled,
                                               train_class=class_name,
                                               exports_path=exports_path,
                                               log_level=log_level
                                               ).create_df_tracks()
    logger.debug("Types of exported files from GT:")
    logger.debug("Type of features: {}".format(type(features)))
    logger.debug("Type of labels: {}".format(type(labels)))
    logger.debug("Type of Tracks: {}".format(type(tracks)))

    model_manage = ClassificationTaskManager(config=config,
                                             train_class=class_name,
                                             X=features,
                                             y=labels,
                                             tracks=tracks,
                                             exports_path=exports_path,
                                             log_level=log_level)
    classification_time = model_manage.apply_processing()
    print(colored("Classification ended successfully in {} minutes.".format(classification_time), "green"))
    logger.info("Classification ended successfully in {} minutes.".format(classification_time))


def update_parameters(config, c_values, gamma_values, preprocessing_values):
    """Update the project file with user-provided preferences

    Args:
        config: The config data to be updated.
        c_values: C value to be updated.
        gamma_values: gamma value to be updated.
        preprocessing_values: preprocessing values to be updated.
    """
    for pref in config['classifiers']['svm']:
        if c_values:
            pref['C'] = c_values
        if gamma_values:
            pref['gamma'] = gamma_values
        if preprocessing_values:
            pref['preprocessing'] = preprocessing_values

    return config

