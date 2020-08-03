import os
from termcolor import colored
from transformation.load_groung_truth import GroundTruthLoad
from classification.classification_task_manager import ClassificationTaskManager
from transformation.load_groung_truth import DatasetExporter
import yaml
from logging_tool import LoggerSetup


def train_class(config, gt_file, log_level):
    exports_path = config["exports_path"]
    gt_data = GroundTruthLoad(config, gt_file, exports_path, log_level)
    # tracks shuffled and exported
    tracks_listed_shuffled = gt_data.export_gt_tracks()

    # class to train
    class_name = gt_data.export_train_class()
    config["class_name"] = class_name

    logger = LoggerSetup(config=config,
                         exports_path=exports_path,
                         name="train_class_{}".format(class_name),
                         train_class=class_name,
                         mode="w",
                         level=log_level).setup_logger()
    
    logger.info("---- TRAINING FOR THE {} MODEL HAS JUST STARTED ----".format(class_name))

    logger.debug("Type of exported GT data exported: {}".format(type(tracks_listed_shuffled)))

    # save project file
    project_file_name_save = "{}_{}.yaml".format(config["project_file"], class_name)
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

    print(colored("Small previews:", "cyan"))
    print(colored("FEATURES", "magenta"))
    print(features.head(3))
    print(colored("LABELS", "magenta"))
    print(labels[:10])
    print(colored("TRACKS:", "magenta"))
    print(tracks[:10])

    model_manage = ClassificationTaskManager(config=config,
                                             train_class=class_name,
                                             X=features,
                                             y=labels,
                                             tracks=tracks,
                                             exports_path=exports_path,
                                             log_level=log_level)
    classification_time = model_manage.apply_processing()
    print(colored("Classification ended in {} minutes.".format(classification_time), "green"))
    logger.info("Classification ended in {} minutes.".format(classification_time))
