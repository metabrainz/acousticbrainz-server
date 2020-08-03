import os
import json
import math
from pprint import pprint
from termcolor import colored
import joblib
from sklearn.model_selection import GridSearchCV
from sklearn.svm import SVC
from sklearn.model_selection import KFold

from transformation.transform import Transform
from utils import load_yaml, FindCreateDirectory, TrainingProcesses
from logging_tool import LoggerSetup


class TrainGridClassifier:
    def __init__(self, config, classifier, class_name, X, y, tr_processes, exports_path, log_level):
        self.config = config
        self.classifier = classifier
        self.class_name = class_name
        self.X = X
        self.y = y
        self.tr_processes = tr_processes
        self.exports_path = exports_path
        self.log_level = log_level

        self.logger = ""
        self.best_models_list = []
        # self.train_grid_search_clf()

        self.setting_logger()

    def setting_logger(self):
        # set up logger
        self.logger = LoggerSetup(config=self.config,
                                  exports_path=self.exports_path,
                                  name="train_class_{}".format(self.class_name),
                                  train_class=self.class_name,
                                  mode="a",
                                  level=self.log_level).setup_logger()

    def train_grid_search_clf(self):
        process_counter = 1
        for tr_process in self.tr_processes:
            print(colored("Train process {} - {}".format(process_counter, tr_process), "green"))
            self.logger.info("(Grid) - Train process {} - {}".format(process_counter, tr_process))
            # initiate SVM classifier object
            if self.classifier == "svm":
                grid_clf = SVC(gamma="auto", probability=True)
            # TODO: different classifier object (e.g. random forests, knn, etc) can be initiated here
            else:
                raise ValueError('The classifier name must be valid.')

            print("CLASSIFIER", tr_process["classifier"])
            # transformation of the data
            features_prepared = Transform(config=self.config,
                                          df_feats=self.X,
                                          process=tr_process["preprocess"],
                                          train_class=self.class_name,
                                          exports_path=self.exports_path,
                                          log_level=self.log_level).post_processing()

            # define the length of parameters
            parameters_grid = {'kernel': tr_process["kernel"],
                               'C': tr_process["C"],
                               'gamma': tr_process["gamma"],
                               'class_weight': tr_process["balanceClasses"]
                               }

            # inner with K-Fold cross-validation declaration
            random_seed = None
            shuffle = self.config["k_fold_shuffle"]
            if shuffle is True:
                random_seed = self.config["seed"]
            elif shuffle is False:
                random_seed = None
            self.logger.info("Fitting the data to the classifier with K-Fold cross-validation..")
            inner_cv = KFold(n_splits=tr_process["n_fold"],
                             shuffle=shuffle,
                             random_state=random_seed
                             )
            # initiate GridSearch Object
            gsvc = GridSearchCV(estimator=grid_clf,
                                param_grid=parameters_grid,
                                cv=inner_cv,
                                n_jobs=self.config["parallel_jobs"],
                                verbose=self.config["verbose"]
                                )

            self.logger.debug("Shape of X before train: {}".format(features_prepared.shape))
            self.logger.info("Fitting the data to the model..")
            gsvc.fit(features_prepared, self.y)

            # print(gsvc.cv_results_["params"])
            self.logger.info("Results from each best preprocess training:")
            self.logger.info("a) Best score: {}".format(gsvc.best_score_))
            self.logger.info("b) Best estimator: {}".format(gsvc.best_estimator_))
            self.logger.info("c) Best parameters: {}".format(gsvc.best_params_))
            self.logger.info("Counted evaluations in this GridSearch process: {}".format(len(gsvc.cv_results_["params"])))

            # save best results for each train process
            exports_dir = "{}_{}".format(self.config.get("exports_directory"), self.class_name)
            results_path = FindCreateDirectory(self.exports_path,
                                               os.path.join(exports_dir, "results")).inspect_directory()
            results_best_dict_name = "result_{}_{}_best_{}.json"\
                .format(self.class_name, tr_process["preprocess"], gsvc.best_score_)

            results_dict = dict()
            results_dict["score"] = gsvc.best_score_
            results_dict["params"] = gsvc.best_params_
            results_dict["n_fold"] = tr_process['n_fold']
            results_dict["preprocessing"] = tr_process["preprocess"]
            with open(os.path.join(results_path, results_best_dict_name), 'w') as grid_best_json:
                json.dump(results_dict, grid_best_json, indent=4)

            # export parameters that the
            results_params_dict_name = "result_{}_{}_params_{}.json"\
                .format(self.class_name, tr_process["preprocess"], gsvc.best_score_)
            with open(os.path.join(results_path, results_params_dict_name), 'w') as grid_params_json:
                json.dump(gsvc.cv_results_["params"], grid_params_json, indent=0)

            models_path = FindCreateDirectory(self.exports_path,
                                              os.path.join(exports_dir, "models")).inspect_directory()
            best_process_model_path = os.path.join(models_path, "model_grid_{}.pkl".format(tr_process["preprocess"]))
            joblib.dump(gsvc.best_estimator_, best_process_model_path)
            self.logger.info("Grid Best model for the {} process saved.".format(tr_process["preprocess"]))

            # return a list that includes the best models exported from each processing
            self.best_models_list.append(results_dict)

            print(colored("Next train process..", "yellow"))
            process_counter += 1
            print()
            print()
        print(colored("Finishing training processes..", "blue"))
        print()

    def export_best_classifier(self):
        # gather best scores from the exported grid clf models
        scores = [x["score"] for x in self.best_models_list]
        self.logger.info("This is the max score of all the training processes: {}".format(max(scores)))
        for model in self.best_models_list:
            if model["score"] == max(scores):
                self.logger.info("Best {} model parameters:".format(self.class_name))
                # log2 --> convert values to initial parameters' values
                # model["params"]["C"] = math.log2(model["params"]["C"])
                # model["params"]["gamma"] = math.log2(model["params"]["gamma"])
                self.logger.info("{}".format(model))
                best_model_name = "best_model_{}.json".format(self.class_name)
                exports_dir = "{}_{}".format(self.config.get("exports_directory"), self.class_name)
                with open(os.path.join(self.exports_path, exports_dir, best_model_name), "w") as best_model:
                    json.dump(model, best_model, indent=4)
                    self.logger.info("Best {} model parameters saved successfully to disk.".format(self.class_name))
