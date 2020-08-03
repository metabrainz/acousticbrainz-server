import os
import requests
import argparse
from pprint import pprint
import joblib
import json
import pandas as pd
from ..helper_functions.utils import load_yaml, FindCreateDirectory
from ..transformation.utils_preprocessing import flatten_dict_full
from ..transformation.transform_predictions import TransformPredictions
from ..helper_functions.logging_tool import LoggerSetup


class Predict:
    def __init__(self, config, track_low_level, log_level):
        self.config = config
        self.track_low_level = track_low_level
        self.log_level = log_level

        self.class_name = ""
        self.exports_path = ""
        self.exports_dir = ""
        self.best_model = ""
        self.track_feats = dict()

        self.load_best_model()
        # self.setting_logger()
        self.logger = ""
        # self.flat_dict()
        self.df_track = pd.DataFrame()
        self.list_track = []

    def load_best_model(self):
        self.class_name = self.config["class_name"]
        self.exports_path = self.config["exports_path"]
        self.exports_dir = self.config["exports_directory"]

        # self.exports_path = os.path.join(self.exports_path, "{}_{}".format(self.exports_dir, self.class_name))
        best_model_path = os.path.join(self.exports_path,
                                       self.exports_dir,
                                       "best_model_{}.json".format(self.class_name))
        # best_model_path = os.path.join(self.exports_dir, "models", "model_grid_{}.pkl".format[""])
        with open(best_model_path) as json_file:
            self.best_model = json.load(json_file)

    def preprocessing(self):
        self.logger = LoggerSetup(config=self.config,
                                  exports_path=self.exports_path,
                                  name="predict_{}".format(self.class_name),
                                  train_class=self.class_name,
                                  mode="w",
                                  level=self.log_level).setup_logger()

        self.logger.info("Best model:")
        self.logger.info(self.best_model)

        self.logger.info("FLATTENING:")
        try:
            if 'beats_position' in self.track_low_level['rhythm']:
                del self.track_low_level['rhythm']['beats_position']
        except Exception as e:
            self.logger.warning("There is no 'rhythm' key in the low level data. Exception:", e)

        # data dictionary transformed to a fully flattened dictionary
        self.track_feats = dict(flatten_dict_full(self.track_low_level))
        list_track = []
        list_track.append(self.track_feats)
        self.logger.debug("DICT TO DATAFRAME:")
        self.df_track = pd.DataFrame(data=list_track, columns=list_track[0].keys())
        self.logger.debug("TYPE of track structure: {}".format(type(self.df_track)))
        # print(self.df_track)
        # print("Shape of DF", self.df_track.shape)

        self.logger.info("PROCESSING:")
        features_prepared = TransformPredictions(config=self.config,
                                                 df_feats=self.df_track,
                                                 process=self.best_model["preprocessing"],
                                                 train_class=self.class_name,
                                                 exports_path=self.exports_path,
                                                 log_level=self.log_level
                                                 ).post_processing()
        self.logger.debug("Features shape after preparation: {}".format(features_prepared.shape))

        # load the best grid model that is trained with a k-fold cross validation
        # models_path = FindCreateDirectory(self.exports_path,
        #                                   os.path.join(self.exports_dir, "models")).inspect_directory()
        # best_model_path = os.path.join(models_path, "model_grid_{}.pkl".format(self.best_model["preprocessing"]))

        # load the best model that is trained to the whole dataset
        models_path = FindCreateDirectory(self.exports_path, self.exports_dir).inspect_directory()
        best_model_path = os.path.join(models_path, "best_clf_model.pkl")
        clf_loaded = joblib.load(best_model_path)
        predicted = clf_loaded.predict(features_prepared)
        predicted_prob = clf_loaded.predict_proba(features_prepared)
        self.logger.info("Prediction: {}".format(predicted))
        self.logger.info("Classes: {}".format(clf_loaded.classes_))
        self.logger.info("Prediction probabilities: {}".format(predicted_prob))
        predict_list = []
        for pred, pred_probability in zip(predicted, predicted_prob):
            predict_dict = dict()
            predict_dict[self.class_name] = pred
            predict_dict["score"] = max(pred_probability)
            predict_dict["probabilities"] = dict(zip(clf_loaded.classes_, pred_probability))

            predict_list.append(predict_dict)

        self.logger.info("Predictions for the track:")
        self.logger.info("{}".format(predict_list))
        self.logger.debug("Output (Return) predict_list")

        return predict_list


def prediction(exports_path, project_file, mbid, log_level="logging.INFO"):
    # if empty, path is declared as the app's main directory
    try:
        project_data = load_yaml(exports_path, "{}.yaml".format(project_file))
    except Exception as e:
        print('Unable to open project configuration file:', e)
        raise

    url_api = "https://acousticbrainz.org/api/v1/{}/low-level".format(mbid)
    response = requests.get(url=url_api)
    track_low_level_data = response.json()
    if track_low_level_data["metadata"]["tags"]["artist"][0]:
        print("Artist:", track_low_level_data["metadata"]["tags"]["artist"][0])
    if track_low_level_data["metadata"]["tags"]["album"][0]:
        print("Album:", track_low_level_data["metadata"]["tags"]["album"][0])
    if track_low_level_data["metadata"]["tags"]["title"][0]:
        print("Title:", track_low_level_data["metadata"]["tags"]["title"][0])

    prediction_track = Predict(config=project_data,
                               track_low_level=track_low_level_data,
                               log_level=log_level
                               )
    prediction_track.preprocessing()


if __name__ == '__main__':

    parser = argparse.ArgumentParser(
        description='Prediction of a track.')

    parser.add_argument("-p", "--path",
                        dest="exports_path",
                        help="Path where the project file (.yaml) is stored.",
                        required=True)

    parser.add_argument("-f", "--file",
                        dest="project_file",
                        help="Name of the project configuration file (.yaml) that is to be loaded. The .yaml at the"
                             "end of the file is not necessary. Just put the name of the file.",
                        required=True)

    parser.add_argument("-t", "--track",
                        dest="mbid",
                        help="MBID of the the low-level data from the AcousticBrainz API.",
                        required=True)

    parser.add_argument("-l", "--logging",
                        dest="log_level",
                        default="logging.INFO",
                        help="The logging level that will be printed logging.DEBUG, logging.INFO, logging.WARNING, "
                             "logging.ERROR, logging.CRITICAL).",
                        type=str)

    args = parser.parse_args()

    prediction(exports_path=args.exports_path,
               project_file=args.project_file,
               mbid=args.mbid,
               log_level=args.log_level)
