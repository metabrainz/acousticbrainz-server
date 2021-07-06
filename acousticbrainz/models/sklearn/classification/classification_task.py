import logging
import os
import json
from ..classification.classifier_grid import TrainGridClassifier
from ..classification.evaluation import evaluation


logger = logging.getLogger(__name__)


class ClassificationTask:
    """
    This class is the core of the model classification. It loads the relevant classifier to
    be used for training, the features, the labels, and the tracks. It uses a corresponding
    to the configuration file declared class to train the model and then it uses that model
    for evaluation.
    """
    def __init__(self, config, classifier, train_class, training_processes, X, y, exports_path, tracks):
        """
        Args:
            config: The configuration data that contain the settings from the configuration
                template with the parsed arguments in classification project.
            classifier: The classifier name (e.g. svm) that is declared in the classifiers
                list of the configuration data.
            train_class: The class name that is defined in the groundtruth yaml file. It is
                actually the model that will be trained.
            training_processes: The training processes (list) where each item of the list
                contains the set of parameters that will be used in the classifier:
                (Evaluation, classifier, preprocess, kernel, C, gamma, balanceClasses, n_fold)
            X: The features (pandas DataFrame) of the exported data from the DatasetExporter class
            y: The labels (NumPy array) of the target class
            exports_path: Path to where the classification project's results will be stored to.
            tracks: The tracks (numpy.ndarray) that are exported from the Groundtruth file.
        """
        self.config = config
        self.classifier = classifier
        self.train_class = train_class

        self.X = X
        self.y = y
        self.training_processes = training_processes
        self.exports_path = exports_path
        self.tracks = tracks


    def run(self):
        # grid search train
        if self.config["train_kind"] == "grid":
            logger.info("Train Classifier: Classifier with GridSearchCV")
            grid_svm_train = TrainGridClassifier(config=self.config,
                                                 classifier=self.classifier,
                                                 class_name=self.train_class,
                                                 X=self.X,
                                                 y=self.y,
                                                 tr_processes=self.training_processes,
                                                 exports_path=self.exports_path,
                                                 logger=logger
                                                 )
            grid_svm_train.train_grid_search_clf()
            grid_svm_train.export_best_classifier()
        else:
            logger.error("Use a valid classifier in the configuration file.")
        logger.info("Training the classifier is completed successfully.")

        # load best model to check its parameters
        logger.debug("Loading the Best Model..")
        best_model_name = "best_model_{}.json".format(self.train_class)
        with open(os.path.join(self.exports_path, best_model_name)) as best_model_file:
            best_model = json.load(best_model_file)
        logger.debug("BEST MODEL: {}".format(best_model))

        # evaluation
        evaluation(config=self.config,
                   n_fold=best_model["n_fold"],
                   X=self.X, y=self.y,
                   class_name=self.train_class,
                   tracks=self.tracks,
                   process=best_model["preprocessing"],
                   exports_path=self.exports_path,
                   )
