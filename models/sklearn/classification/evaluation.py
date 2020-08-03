import os
import json
import numpy as np
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from termcolor import colored
import yaml
from sklearn.model_selection import KFold
from sklearn.metrics import accuracy_score
from sklearn.metrics import confusion_matrix, classification_report
import joblib

from ..helper_functions.utils import FindCreateDirectory
from ..transformation.transform import Transform
from ..classification.report_files_export import export_report
from ..helper_functions.logging_tool import LoggerSetup


def evaluation(config, n_fold, X, y, class_name, tracks, process, exports_path, log_level):
    print(colored("------ EVALUATION and FOLDING ------", "yellow"))
    logger = LoggerSetup(config=config,
                         exports_path=exports_path,
                         name="train_model_{}".format(class_name),
                         train_class=class_name,
                         mode="a",
                         level=log_level).setup_logger()

    logger.info("---- Folded evaluation of the model in the dataset ----")
    logger.info("number of folds set to config: {}".format(n_fold))
    logger.debug("Sample of shuffled tracks tracks:")
    logger.debug("{}".format(tracks[:5]))
    logger.debug("Tracks list length: {}".format(len(tracks)))

    # load project directory and the corresponding save paths
    exports_dir = config.get("exports_directory")

    dataset_path = FindCreateDirectory(exports_path,
                                       os.path.join(exports_dir, "dataset")).inspect_directory()
    models_path = FindCreateDirectory(exports_path,
                                      os.path.join(exports_dir, "models")).inspect_directory()
    images_path = FindCreateDirectory(exports_path,
                                      os.path.join(exports_dir, "images")).inspect_directory()

    # load best model
    load_model_params_path = os.path.join(exports_path, exports_dir, "best_model_{}.json".format(class_name))
    with open(load_model_params_path) as model_params_file:
        model_params_data = json.load(model_params_file)

    logger.info("Best model preprocessing step: {}".format(process))
    # load the saved classifier
    clf = joblib.load(os.path.join(models_path, "model_grid_{}.pkl".format(process)))
    logger.info("Best model loaded.")

    # inner K-Fold cross-validation declaration
    random_seed = None
    shuffle = config["k_fold_shuffle"]
    if shuffle is True:
        random_seed = config["seed"]
    elif shuffle is False:
        random_seed = None
    logger.info("Fitting the data to the classifier with K-Fold cross-validation..")
    inner_cv = KFold(n_splits=n_fold,
                     shuffle=shuffle,
                     random_state=random_seed)

    # transformation of the data to proper features based on the preprocess step
    features_prepared = Transform(config=config,
                                  df_feats=X,
                                  process=process,
                                  train_class=class_name,
                                  exports_path=exports_path,
                                  log_level=log_level).post_processing()
    logger.debug("Features prepared shape: {}".format(features_prepared.shape))

    # Starting Training, Predictions for each fold
    logger.info("Starting fold-evaluation..")
    predictions_df_list, accuracy_model, tracks_fold_indexing_dict = predictions_fold(clf=clf,
                                                                                      inner_cv=inner_cv,
                                                                                      feats_prepared=features_prepared,
                                                                                      y=y,
                                                                                      tracks=tracks,
                                                                                      class_name=class_name,
                                                                                      logger=logger)

    # concatenate the folded predictions DFs
    df_predictions = create_dataset_predictions(list_df_predictions=predictions_df_list,
                                                class_name=class_name,
                                                dataset_path=dataset_path,
                                                logger=logger)

    # ACCURACIES in each fold
    export_accuracies(accuracy_model=accuracy_model,
                      config=config,
                      class_name=class_name,
                      exports_path=exports_path,
                      images_path=images_path,
                      logger=logger)

    # Folded Tracks Dictionary
    export_folded_instances(tracks_fold_indexing_dict=tracks_fold_indexing_dict,
                            class_name=class_name,
                            dataset_path=dataset_path,
                            logger=logger)

    # Evaluation to the folded Dataset
    export_evaluation_results(config=config,
                              set_name="Folded",
                              y_true_values=df_predictions[class_name],
                              predictions=df_predictions["predictions"],
                              class_name=class_name,
                              exports_path=exports_path,
                              logger=logger
                              )

    # Train to the whole dataset
    logger.info("Train the classifier with the whole dataset..")
    clf.fit(features_prepared, y)
    # prediction for the whole dataset
    predictions_all = clf.predict(features_prepared)
    # save the model that is trained to the whole dataset
    best_model_path = os.path.join(exports_path, exports_dir, "best_clf_model.pkl")
    joblib.dump(clf, best_model_path)
    logger.info("Best model saved.")
    # Evaluation to the whole Dataset
    export_evaluation_results(config=config,
                              set_name="Whole",
                              y_true_values=y,
                              predictions=predictions_all,
                              class_name=class_name,
                              exports_path=exports_path,
                              logger=logger
                              )


def predictions_fold(clf, inner_cv, feats_prepared, y, tracks, class_name, logger):
    tracks_fold_indexing_dict = {}
    accuracy_model = []
    predictions_df_list = []
    fold_number = 0
    for train_index, test_index in inner_cv.split(feats_prepared):
        logger.info("FOLD {} - Analyzing, Fitting, Predicting".format(fold_number))
        logger.debug("first test index element: {} - last test index element: {}".format(test_index[0], test_index[-1]))
        logger.debug("TEST INDEX: {}".format(test_index))
        logger.debug("Length of the test index array: {}".format(len(test_index)))

        # tracks indexing list for each fold
        tracks_count = 0
        tracks_list = []
        for index in test_index:
            tracks_fold_indexing_dict[tracks[index]] = fold_number
            tracks_list.append(tracks[index])
            tracks_count += 1
        logger.debug("Tracks indexed to the specific fold: {}".format(tracks_count))
        X_train, X_test = feats_prepared[train_index], feats_prepared[test_index]
        y_train, y_test = y[train_index], y[test_index]
        # Train the model
        clf.fit(X_train, y_train)
        logger.debug("Classifier classes: {}".format(clf.classes_))
        # create a df for this fold with the predictions
        df_pred_general = fold_predictions(clf=clf,
                                           class_name=class_name,
                                           X_test=X_test,
                                           test_index=test_index,
                                           tracks_list=tracks_list,
                                           y_test=y_test,
                                           logger=logger)
        # Append the folded dataset to a list that will contain all the folded datasets:
        predictions_df_list.append(df_pred_general)
        # Append each accuracy of the folded model to a list that contains all the accuracies resulted from each fold
        accuracy_model.append(accuracy_score(y_test, clf.predict(X_test), normalize=True) * 100)
        fold_number += 1

    return predictions_df_list, accuracy_model, tracks_fold_indexing_dict


def fold_predictions(clf, class_name, X_test, test_index, tracks_list, y_test, logger):
    """
    Creates a pandas DataFrame from each fold with the predictions in
    order later to extract the shuffled dataset with the tracks, the percentage
    of the prediction probability for each class, the prediction, and the true
    value.

    Args:
        clf:
        class_name:
        X_test:
        test_index:
        tracks_list:
        y_test:
        logger:

    Returns:
        A pandas DataFrame with the predictions at each fold.
    """
    # predictions for the features test
    pred = clf.predict(X_test)
    # predictions numpy array transformation to pandas DF
    df_pred = pd.DataFrame(data=pred, index=test_index, columns=["predictions"])
    # predictions' probabilities
    pred_prob = clf.predict_proba(X_test)
    # predictions' probabilities numpy array transformation to pandas DF
    df_pred_prob = pd.DataFrame(data=pred_prob, index=test_index, columns=clf.classes_)
    # tracks list transformation to pandas DF
    df_tracks = pd.DataFrame(data=tracks_list, index=test_index, columns=["track"])
    logger.debug("\n{}".format(df_tracks.head()))
    # y_test pandas Series transformation to pandas DF
    y_test_series = pd.DataFrame(data=y_test, index=test_index, columns=[class_name])
    # concatenate the 4 DFs above to 1 for saving the resulted dataset
    # (tracks, predictions' probabilities, predictions, true)
    logger.debug("Concatenating DF..")
    df_pred_general = pd.concat([df_tracks, df_pred_prob, df_pred, y_test_series], axis=1, ignore_index=False)

    return df_pred_general


def export_accuracies(accuracy_model, config, class_name, exports_path, images_path, logger):
    logger.info("Accuracies in each fold: {}".format(accuracy_model))
    logger.info("Mean of accuracies: {}".format(np.mean(accuracy_model)))
    logger.info("Standard Deviation of accuracies: {}".format(np.std(accuracy_model)))
    accuracies_export = "Accuracies in each fold: {} \nMean of accuracies: {} \nStandard Deviation of accuracies: {}" \
        .format(accuracy_model, np.mean(accuracy_model), np.std(accuracy_model))
    export_report(config=config,
                  name="Accuracies results",
                  report=accuracies_export,
                  filename="accuracies_results_fold",
                  train_class=class_name,
                  exports_path=exports_path)

    # Visualize accuracy for each iteration in a distribution plot
    create_accuracies_dist_plot(accuracies_list=accuracy_model,
                                images_path=images_path,
                                logger=logger)


def create_dataset_predictions(list_df_predictions, class_name, dataset_path, logger):
    logger.info("Make Predictions DataFrame for all the folded instances together.")
    df_concat_predictions = pd.concat(list_df_predictions)
    logger.debug("\n{}".format(df_concat_predictions.head()))
    logger.debug("Info:")
    logger.debug("\n{}".format(df_concat_predictions.info()))
    # save predictions df
    logger.info("Saving the unified predictions DataFrame locally.")
    df_concat_predictions.to_csv(os.path.join(dataset_path, "predictions_{}.csv".format(class_name)))

    return df_concat_predictions


def create_accuracies_dist_plot(accuracies_list, images_path, logger):
    logger.info("Visualize accuracy for each iteration.")
    list_folds = []
    counter_folds = 0
    for accuracy in accuracies_list:
        list_folds.append("Fold{}".format(counter_folds))
        counter_folds += 1
    logger.debug("Exporting accuracies distribution to plot file..")
    scores = pd.DataFrame(accuracies_list, columns=['Scores'])
    sns.set(style="white", rc={"lines.linewidth": 3})
    sns.barplot(x=list_folds, y="Scores", data=scores)
    plt.savefig(os.path.join(images_path, "accuracies_distribution.png"))
    sns.set()
    plt.close()
    logger.info("Plot saved successfully.")


def export_folded_instances(tracks_fold_indexing_dict, class_name, dataset_path, logger):
    logger.info("Writing Folded Tracks Dictionary locally to check where each track is folded..")
    logger.debug("length of keys: {}".format(len(tracks_fold_indexing_dict.keys())))
    folded_dataset_path = os.path.join(dataset_path, "{}.yaml".format(class_name))
    with open(folded_dataset_path, 'w') as file:
        folded_dataset = yaml.dump(tracks_fold_indexing_dict, file)
    logger.info("Folded dataset written successfully to disk.")


def export_evaluation_results(config, set_name, y_true_values, predictions, class_name, exports_path, logger):
    logger.info("---- Evaluation to the {} dataset ----".format(set_name))
    # Confusion Matrix
    logger.info("Exporting Confusion Matrix applied to the {} dataset..".format(set_name))
    cm = confusion_matrix(y_true=y_true_values, y_pred=predictions)
    logger.info("\n{}".format(cm))
    # Confusion Matrix Normalized
    logger.info("Exporting Normalized Confusion Matrix applied to the {} dataset..".format(set_name))
    cm_normalized = (cm / cm.astype(np.float).sum(axis=1) * 100)
    logger.info("\n{}".format(cm_normalized))
    cm_all = "Actual instances\n{}\n\nNormalized\n{}".format(cm, cm_normalized)
    # export the confusion matrix report for the folded dataset
    export_report(config=config,
                  name="{} Data Confusion Matrix".format(set_name),
                  report=cm_all,
                  filename="confusion_matrix_{}".format(set_name),
                  train_class=class_name,
                  exports_path=exports_path)
    # Classification Report
    logger.info("Exporting Classification Report applied to the {} dataset..".format(set_name))
    cr = classification_report(y_true=y_true_values, y_pred=predictions)
    # export the Classification report for the whole dataset
    export_report(config=config,
                  name="{} Data Classification Report".format(set_name),
                  report=cr,
                  filename="classification_report_{}".format(set_name),
                  train_class=class_name,
                  exports_path=exports_path)
    logger.info("The {} dataset has been evaluated successfully.".format(set_name))
