import logging
import os
from time import time
from termcolor import colored
from datetime import datetime

from ..helper_functions.utils import create_directory, TrainingProcesses
from ..classification.classification_task import ClassificationTask


logger = logging.getLogger(__name__)

validClassifiers = ["svm", "NN"]
validEvaluations = ["nfoldcrossvalidation"]


class ClassificationTaskManager:
    """
    It manages the tasks to be done based on the configuration file. It checks if the
    config keys exist in the template and are specified correctly, as well as it creates
    the relevant directories (if not exist) where the classification results will be
    stored to. Then, it extracts a list with the evaluation steps that will be followed
    with their corresponding preprocessing steps and parameters declaration for the
    classifier, and executes the classification task for each step.
    """
    def __init__(self, config, train_class, X, y, tracks, exports_path):
        """
        Args:
            config: The configuration file name.
            train_class: The class that will be trained.
            X: The already shuffled data that contain the features.
            y: The already shuffled data that contain the labels.
        """
        self.config = config
        self.train_class = train_class
        self.X = X
        self.y = y
        self.tracks = tracks
        self.exports_path = exports_path

        self.results_path = ""
        self.logs_path = ""
        self.tracks_path = ""
        self.dataset_path = ""
        self.models_path = ""
        self.images_path = ""
        self.reports_path = ""

        self.files_existence()
        self.config_file_analysis()


    def files_existence(self):
        """
        Ensure that all the folders will exist before the training process starts.
        """
        # main exports
        # train results exports
        self.results_path = create_directory(self.exports_path, "results")
        # logs
        self.logs_path = create_directory(self.exports_path, "logs")
        # tracks
        self.tracks_path = create_directory(self.exports_path, "tracks_csv_format")
        # datasets
        self.dataset_path = create_directory(self.exports_path, "dataset")
        # models
        self.models_path = create_directory(self.exports_path, "models")
        # images
        self.images_path = create_directory(self.exports_path, "images")
        # reports
        self.reports_path = create_directory(self.exports_path, "reports")

    def config_file_analysis(self):
        """
        Check the keys of the configuration template file if they are set up correctly.
        """
        logger.info("---- CHECK FOR INAPPROPRIATE CONFIG FILE FORMAT ----")
        if "processing" not in self.config:
            logger.error("No preprocessing defined in config.")

        if "evaluations" not in self.config:
            logger.error("No evaluations defined in config.")
            logger.error("Setting default evaluation to 10-fold cross-validation")
            self.config["evaluations"] = {"nfoldcrossvalidation": [{"nfold": [10]}]}

        for classifier in self.config['classifiers'].keys():
            if classifier not in validClassifiers:
                logger.error("Not a valid classifier: {}".format(classifier))
                raise ValueError("The classifier name must be valid.")

        for evaluation in self.config['evaluations'].keys():
            if evaluation not in validEvaluations:
                logger.error("Not a valid evaluation: {}".format(evaluation))
                raise ValueError("The evaluation must be valid.")
        logger.info("No errors in config file format found.")

    def apply_processing(self):
        """
        Evaluation steps extraction and classification task execution for each step.
        """
        start_time = time()
        training_processes = TrainingProcesses(self.config).training_processes()
        logger.info("Classifiers detected: {}".format(self.config["classifiers"].keys()))
        for classifier in self.config["classifiers"].keys():
            print("Before Classification task: ", classifier)
            task = ClassificationTask(config=self.config,
                                      classifier=classifier,
                                      train_class=self.train_class,
                                      training_processes=training_processes,
                                      X=self.X,
                                      y=self.y,
                                      exports_path=self.exports_path,
                                      tracks=self.tracks,
                                      )
            try:
                task.run()
            except Exception as e:
                logger.error('Running task failed: {}'.format(e))
                print(colored('Running task failed: {}'.format(e), "red"))
        end_time = time()

        print()
        print(colored("Last evaluation took place at: {}".format(datetime.now()), "magenta"))
        logger.info("Last evaluation took place at: {}".format(datetime.now()))

        # test duration
        time_duration = end_time - start_time
        classification_time = round(time_duration / 60, 2)
        return classification_time
