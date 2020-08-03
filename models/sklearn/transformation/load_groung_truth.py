import os
import yaml
import pandas as pd
from pprint import pprint
from termcolor import colored
import random
from utils import load_yaml, FindCreateDirectory
from transformation.load_low_level import FeaturesDf
from logging_tool import LoggerSetup


class ListGroundTruthFiles:
    """

    """
    def __init__(self, config):
        """

        :param config:
        """
        self.config = config
        self.dataset_dir = ""
        self.class_dir = ""

    def list_gt_filenames(self):
        """

        :return:
        """
        self.dataset_dir = self.config.get("ground_truth_directory")
        self.class_dir = self.config.get("class_dir")
        path = os.path.join(os.getcwd(), self.dataset_dir, self.class_dir, "metadata")
        ground_truth_list = [filename for filename in os.listdir(os.path.join(path))
                             if filename.startswith("groundtruth")]
        return ground_truth_list


class GroundTruthLoad:
    """
        The Ground Truth data object which contains features to:
         * counter the JSON low-level data
         * Todo: create logger object

         Attributes:
        """
    def __init__(self, config, gt_filename, exports_path, log_level):
        """

        :param config:
        :param gt_filename:
        """
        self.config = config
        self.gt_filename = gt_filename
        self.exports_path = exports_path
        self.log_level = log_level

        self.logger = ""
        self.class_dir = ""
        self.ground_truth_data = {}
        self.labeled_tracks = {}
        self.train_class = ""
        self.dataset_dir = ""
        self.tracks = []

        self.load_local_ground_truth()

    def load_local_ground_truth(self):
        """
        Loads the the ground truth file.
        * The directory with the dataset should be located inside the app folder location.
        :return:
        """

        self.dataset_dir = self.config.get("ground_truth_directory")
        self.class_dir = self.config.get("class_dir")
        with open(os.path.join(os.getcwd(), "{}/{}/metadata/{}".format(
                self.dataset_dir, self.class_dir, self.gt_filename)), "r") as stream:
            try:
                self.ground_truth_data = yaml.safe_load(stream)
                print("Ground truth file loaded.")
            except yaml.YAMLError as exc:
                print("Error in loading the ground truth file.")
                print(exc)

    def export_train_class(self):
        """

        :return:
        """
        self.train_class = self.ground_truth_data["className"]
        print("EXPORT CLASS NAME: {}".format(self.train_class))
        return self.train_class

    def export_gt_tracks(self):
        self.labeled_tracks = self.ground_truth_data["groundTruth"]
        tracks_list = []
        for track, label in self.labeled_tracks.items():
            tracks_list.append((track, label))
        print(colored("SEED is set to: {}".format(self.config.get("seed"), "cyan")))
        random.seed(a=self.config.get("seed"))
        random.shuffle(tracks_list)
        return tracks_list

    def check_ground_truth_data(self):
        """
        Todo: description
        :return:
        """
        pprint(self.ground_truth_data)

    def check_ground_truth_info(self):
        """
        Todo: description
        :return:
        """
        len(self.ground_truth_data["groundTruth"].keys())
        print("Ground truth data class/target: {}".format(self.ground_truth_data["className"]))
        print("Label tracks: {}".format(type(self.labeled_tracks)))
        print("Ground truth data keys - tracks: {}".format(len(self.ground_truth_data["groundTruth"].keys())))

    def check_tracks_folders(self):
        """
        Todo: function explanation docstring
        :return:
        """
        if len(self.labeled_tracks.keys()) is not 0:
            folders = []
            for key in self.labeled_tracks:
                key = key.split('/')
                path_sub_dir = '/'.join(key[:-1])
                folders.append(path_sub_dir)
            folders = set(folders)
            folders = list(folders)
            folders.sort()
            print("Directories that contain the low-level JSON data:")
            print("{}".format(folders))

    def count_json_low_level_files(self):
        """
        Prints the JSON low-level data that is contained inside the dataset directory (the dataset
        directory is declared in configuration file).
        :return:
        """
        counter = 0
        for root, dirs, files in os.walk(os.path.join(os.getcwd(), self.dataset_dir)):
            for file in files:
                if file.endswith(".json"):
                    # print(os.path.join(root, file))
                    counter += 1
        print("counted json files: {}".format(counter))


class DatasetExporter:
    def __init__(self, config, tracks_list, train_class, exports_path, log_level):
        self.config = config
        self.tracks_list = tracks_list
        self.train_class = train_class
        self.exports_path = exports_path
        self.log_level = log_level

        self.dataset_dir = ""
        self.class_dir = ""
        self.df_tracks = pd.DataFrame()
        self.df_feats = pd.DataFrame()
        self.y = []
        self.logger = ""

        self.setting_logger()

    def setting_logger(self):
        # set up logger
        self.logger = LoggerSetup(config=self.config,
                                  exports_path=self.exports_path,
                                  name="dataset_exports_transformations_{}".format(self.train_class),
                                  train_class=self.train_class,
                                  mode="w",
                                  level=self.log_level).setup_logger()

    def create_df_tracks(self):
        """
        Creates the pandas DataFrame with the tracks.
        Todo: more comments
        :return:
        DataFrame or None: a DataFrame with the tracks included in the ground truth yaml file containing the track name,
        the path to load the JSON low-level data, the label, etc. Else, it returns None.
        """

        self.logger.info("---- EXPORTING FEATURES - LABELS - TRACKS ----")
        # the class name from the ground truth data that is the target
        self.dataset_dir = self.config.get("ground_truth_directory")
        self.class_dir = self.config.get("class_dir")
        print('DATASET-DIR', self.dataset_dir)
        print('CLASS NAME PATH', self.class_dir)
        # the path to the "features" directory that contains the rest of the low-level data sub-directories
        path_features = os.path.join(os.getcwd(), self.dataset_dir, self.class_dir, "features")
        # check if the "features" directory is empty or contains the "mp3" or the "orig" sub-directory
        low_level_dir = ""
        if len(os.listdir(path_features)) == 0:
            print("Directory is empty")
            self.logger.warning("Directory is empty.")
        else:
            print("Directory is not empty")
            self.logger.info("Directory is not empty")
            directory_contents = os.listdir(path_features)
            if "mp3" in directory_contents:
                low_level_dir = "mp3"
            elif "orig" in directory_contents:
                low_level_dir = "orig"
            else:
                low_level_dir = ""
                print("There is no valid low-level data inside the features directory")
                self.logger.warning("There is no valid low-level data inside the features directory")
        # print which directory contains the low-level sub-directories (if exist)
        self.logger.info("Low-level directory name that contains the data: {}".format(low_level_dir))
        # path to the low-level data sub-directories
        path_low_level = os.path.join(os.getcwd(), self.dataset_dir, self.class_dir, "features", low_level_dir)
        self.logger.info("Path of low level data: {}".format(path_low_level))
        # create a list with dictionaries that contain the information from each track in
        if low_level_dir != "":
            self.df_tracks = pd.DataFrame(data=self.tracks_list, columns=["track", self.train_class])
            self.logger.debug("Shape of tracks DF created before cleaning: {}".format(self.df_tracks.shape))
            self.logger.debug("Check the shape of a temporary DF that includes if there are any NULL values:")
            self.logger.debug("{}".format(self.df_tracks[self.df_tracks.isnull().any(axis=1)].shape))

            self.logger.debug("Drop rows with NULL values if they exist..")
            if self.df_tracks[self.df_tracks.isnull().any(axis=1)].shape[0] != 0:
                self.df_tracks.dropna(inplace=True)
                self.logger.debug("Check if there are NULL values after the cleaning process:")
                self.logger.debug("{}".format(self.df_tracks[self.df_tracks.isnull().any(axis=1)].shape))
                self.logger.debug("Re-index the tracks DF..")
                self.df_tracks = self.df_tracks.reset_index(drop=True)
            else:
                self.logger.info("There are no NULL values found.")

            # export shuffled tracks to CSV format
            exports_dir = "{}_{}".format(self.config.get("exports_directory"), self.train_class)
            tracks_path = FindCreateDirectory(self.exports_path,
                                              os.path.join(exports_dir, "tracks_csv_format")).inspect_directory()
            self.df_tracks.to_csv(os.path.join(tracks_path, "tracks_{}_shuffled.csv".format(self.train_class)))
            self.logger.debug("DF INFO:")
            self.logger.debug("{}".format(self.df_tracks.info()))
            self.logger.debug("COLUMNS CONTAIN OBJECTS: {}".format(
                self.df_tracks.select_dtypes(include=['object']).columns))

            self.df_feats = FeaturesDf(df_tracks=self.df_tracks,
                                       train_class=self.train_class,
                                       path_low_level=path_low_level,
                                       config=self.config,
                                       exports_path=self.exports_path,
                                       log_level=self.log_level,
                                       ).create_low_level_df()

            self.y = self.df_tracks[self.train_class].values
            self.logger.info("Features, Labels, and Tracks are exported successfully..")
            return self.df_feats, self.y, self.df_tracks["track"].values
        else:
            return None, None, None
