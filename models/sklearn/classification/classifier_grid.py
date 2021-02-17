import os
import json
from termcolor import colored
import joblib
from sklearn.model_selection import GridSearchCV
from sklearn.svm import SVC
from sklearn.model_selection import KFold

from ..transformation.transform import Transform
from ..helper_functions.utils import FindCreateDirectory
from ..helper_functions.logging_tool import LoggerSetup


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
        self.logger = LoggerSetup(config=self.config,
                                  exports_path=self.exports_path,
                                  name="train_model_{}".format(self.class_name),
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

            # train the grid classifier and return the trained model
            gsvc = train_grid(tr_process=tr_process,
                              grid_clf=grid_clf,
                              features_prepared=features_prepared,
                              y=self.y,
                              config=self.config,
                              logger=self.logger)

            # save best results for each train process
            exports_dir = self.config.get("exports_directory")
            # paths declaration for saving the grid training results
            results_path = FindCreateDirectory(self.exports_path,
                                               os.path.join(exports_dir, "results")).inspect_directory()
            models_path = FindCreateDirectory(self.exports_path,
                                              os.path.join(exports_dir, "models")).inspect_directory()
            best_process_model_path = os.path.join(models_path, "model_grid_{}.pkl".format(tr_process["preprocess"]))

            # save the results from each train process step and return the results from that train in a dictionary
            # that contains: the best score, the best params, the number of folds, and the preprocessing step
            results_dict = save_grid_results(gsvc=gsvc,
                                             class_name=self.class_name,
                                             tr_process=tr_process,
                                             results_path=results_path,
                                             best_process_model_path=best_process_model_path,
                                             logger=self.logger)

            # return a list that includes the best models exported from each processing
            self.best_models_list.append(results_dict)

            print(colored("Next train process..", "yellow"))
            process_counter += 1
            print()
            print()
        print(colored("Finishing training processes..", "blue"))
        print()

    def export_best_classifier(self):
        # Gather the best scores from the exported grid clf models
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
                exports_dir = self.config.get("exports_directory")
                with open(os.path.join(self.exports_path, exports_dir, best_model_name), "w") as best_model:
                    json.dump(model, best_model, indent=4)
                    self.logger.info("Best {} model parameters saved successfully to disk.".format(self.class_name))


def train_grid(tr_process, grid_clf, features_prepared, y, config, logger):
    # define the length of parameters
    parameters_grid = {'kernel': tr_process["kernel"],
                       'C': tr_process["C"],
                       'gamma': tr_process["gamma"],
                       'class_weight': tr_process["balance_classes"]
                       }

    # inner with K-Fold cross-validation declaration
    random_seed = None
    shuffle = config["k_fold_shuffle"]
    if shuffle is True:
        random_seed = config["seed"]
    elif shuffle is False:
        random_seed = None
    logger.info("Fitting the data to the classifier with K-Fold cross-validation..")
    inner_cv = KFold(n_splits=tr_process["n_fold"],
                     shuffle=shuffle,
                     random_state=random_seed
                     )
    # initiate GridSearch Object
    gsvc = GridSearchCV(estimator=grid_clf,
                        param_grid=parameters_grid,
                        cv=inner_cv,
                        n_jobs=config["parallel_jobs"],
                        verbose=config["verbose"]
                        )

    logger.debug("Shape of X before train: {}".format(features_prepared.shape))
    logger.info("Fitting the data to the model..")
    gsvc.fit(features_prepared, y)

    logger.info("Results from each best preprocess training:")
    logger.info("a) Best score: {}".format(gsvc.best_score_))
    logger.info("b) Best estimator: {}".format(gsvc.best_estimator_))
    logger.info("c) Best parameters: {}".format(gsvc.best_params_))
    logger.info("Counted evaluations in this GridSearch process: {}".format(len(gsvc.cv_results_["params"])))

    return gsvc


def save_grid_results(gsvc, class_name, tr_process, results_path, best_process_model_path, logger):
    results_best_dict_name = "result_{}_{}_best_{}.json" \
        .format(class_name, tr_process["preprocess"], gsvc.best_score_)

    results_dict = {
        "score": gsvc.best_score_,
        "params": gsvc.best_params_,
        "n_fold": tr_process['n_fold'],
        "preprocessing": tr_process["preprocess"]
    }
    with open(os.path.join(results_path, results_best_dict_name), 'w') as grid_best_json:
        json.dump(results_dict, grid_best_json, indent=4)

    # export the parameters that the best model has from each training step
    results_params_dict_name = "result_{}_{}_params_{}.json" \
        .format(class_name, tr_process["preprocess"], gsvc.best_score_)
    with open(os.path.join(results_path, results_params_dict_name), 'w') as grid_params_json:
        json.dump(gsvc.cv_results_["params"], grid_params_json, indent=0)

    joblib.dump(gsvc.best_estimator_, best_process_model_path)
    logger.info("Grid Best model for the {} process saved.".format(tr_process["preprocess"]))

    return results_dict
