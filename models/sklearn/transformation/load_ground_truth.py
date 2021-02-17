import os
import yaml
import pandas as pd
from pprint import pprint
from termcolor import colored
import random
from ..helper_functions.utils import load_yaml, FindCreateDirectory
from ..transformation.load_low_level import FeaturesDf
from ..helper_functions.logging_tool import LoggerSetup


class ListGroundTruthFiles:
    """
    Lists the groundtruth yaml files that are detected in a folder specified in
    the configuration file. The yaml files contain the target class and the tracks
    to be analyzed.
    """
    def __init__(self, config):
        """
        Args:
            config: The configuration data
        """
        self.config = config
        self.dataset_dir = ""

    def list_gt_filenames(self):
        """
        Returns:
            A list of the groundtruth detected yaml files.
        """
        self.dataset_dir = self.config.get("ground_truth_directory")
        ground_truth_list = list()
        dirpath = os.path.join(os.getcwd(), self.dataset_dir)
        for (dirpath, dirnames, filenames) in os.walk(dirpath):
            ground_truth_list += [os.path.join(dirpath, file) for file in filenames if file.startswith("groundtruth")]
        return ground_truth_list


class GroundTruthLoad:
    """
        The Ground Truth data which contains the tracks and the corresponding
        labels they belong to. The path to the related tracks' low-level data
        (features in JSON format) can be extracted from this file too.
        """
    def __init__(self, config, gt_filename, exports_path, log_level):
        """
        Args:
            config:
            gt_filename:
            exports_path:
            log_level:
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
        Loads the the ground truth file. The dataset directory is specified through
        the parsing arguments of the create_classification_project method.
        """
        self.dataset_dir = self.config.get("dataset_dir")
        with open(self.gt_filename, "r") as stream:
            try:
                self.ground_truth_data = yaml.safe_load(stream)
                print("Ground truth file loaded.")
            except yaml.YAMLError as exc:
                print("Error in loading the ground truth file.")
                print(exc)

    def export_train_class(self):
        """
        Returns:
            The target class to be modeled.
        """
        self.train_class = self.ground_truth_data["className"]
        print("EXPORT CLASS NAME: {}".format(self.train_class))
        return self.train_class

    def export_gt_tracks(self):
        """
        It takes a dictionary of the tracks from the groundtruth and it transforms it
        to a list of tuples (track, label). Then it shuffles the list based on the seed
        specified in the configuration file, and returns that shuffled list.
        Returns:
            A list of tuples with the tracks and their corresponding labels.
        """
        self.labeled_tracks = self.ground_truth_data["groundTruth"]
        tracks_list = []
        for track, label in self.labeled_tracks.items():
            tracks_list.append((track, label))
        print(colored("SEED is set to: {}".format(self.config.get("seed"), "cyan")))
        random.seed(a=self.config.get("seed"))
        random.shuffle(tracks_list)
        print("Listed tracks in GT file: {}".format(len(tracks_list)))
        return tracks_list

    def check_ground_truth_data(self):
        """
        Prints a dictionary of the groundtruth data in the corresponding yaml file.
        It contains the target class and the tracks.
        """
        pprint(self.ground_truth_data)

    def check_ground_truth_info(self):
        """
        Prints information about the groundtruth data that is loaded in a dictionary:
            * The target class
            * The tracks with their labels
            * The tracks themselves
        """
        len(self.ground_truth_data["groundTruth"].keys())
        print("Ground truth data class/target: {}".format(self.ground_truth_data["className"]))
        print("Label tracks: {}".format(type(self.labeled_tracks)))
        print("Ground truth data keys - tracks: {}".format(len(self.ground_truth_data["groundTruth"].keys())))

    def check_tracks_folders(self):
        """
        Prints the directories that contain the low-level data.
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
        """
        counter = 0
        for root, dirs, files in os.walk(os.path.join(os.getcwd(), self.dataset_dir)):
            for file in files:
                if file.endswith(".json"):
                    # print(os.path.join(root, file))
                    counter += 1
        print("counted json files: {}".format(counter))


class DatasetExporter:
    """
    TODO: Description
    """
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
        self.logger = LoggerSetup(config=self.config,
                                  exports_path=self.exports_path,
                                  name="train_model_{}".format(self.train_class),
                                  train_class=self.train_class,
                                  mode="a",
                                  level=self.log_level).setup_logger()

    def create_df_tracks(self):
        """
        TODO: Description
        Returns:
            TODO: Description
        """

        self.logger.info("---- EXPORTING FEATURES - LABELS - TRACKS ----")
        # the class name from the ground truth data that is the target
        self.dataset_dir = self.config.get("ground_truth_directory")
        # self.class_dir = self.config.get("class_dir")
        print('DATASET-DIR', self.dataset_dir)
        # print('CLASS NAME PATH', self.class_dir)
        dirpath = os.path.join(os.getcwd(), self.dataset_dir)
        low_level_list = list()
        for (dirpath, dirnames, filenames) in os.walk(dirpath):
            low_level_list += [os.path.join(dirpath, file) for file in filenames if file.endswith(".json")]
        if len(low_level_list) != 0:
            self.logger.info("Low-level features for the tracks found.")
            # processing the names of the tracks that are inside both the GT file and the low-level json files
            # list with the tracks that are included in the low-level json files
            tracks_existing_list = [e for e in self.tracks_list for i in low_level_list if e[0] in i]
            # list with the low-level json tracks' paths that are included in tracks list
            tracks_existing_path_list = [i for e in self.tracks_list for i in low_level_list if e[0] in i]
            self.logger.debug("tracks existed found: {}".format(len(tracks_existing_list)))
            self.logger.debug("tracks_path existed found: {}".format(len(tracks_existing_path_list)))
            self.logger.debug("{}".format(tracks_existing_list[:4]))
            self.logger.debug("{}".format(tracks_existing_path_list[:4]))
            self.logger.debug("The founded tracks tracks listed successfully.")
            self.logger.debug("Generate random number within a given range of listed tracks:")
            # Random number between 0 and length of listed tracks
            random_num = random.randrange(len(tracks_existing_list))
            self.logger.debug("Check if the tracks are the same in the same random index in both lists")
            self.logger.debug("{}".format(tracks_existing_list[random_num]))
            self.logger.debug("{}".format(tracks_existing_path_list[random_num]))

            self.tracks_list = tracks_existing_list
            # create the dataframe with tracks that are bothe in low-level files and the GT file
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
            exports_dir = self.config.get("exports_directory")
            tracks_path = FindCreateDirectory(self.exports_path,
                                              os.path.join(exports_dir, "tracks_csv_format")).inspect_directory()
            self.df_tracks.to_csv(os.path.join(tracks_path, "tracks_{}_shuffled.csv".format(self.train_class)))
            self.logger.debug("DF INFO:")
            self.logger.debug("{}".format(self.df_tracks.info()))
            self.logger.debug("COLUMNS CONTAIN OBJECTS: {}".format(
                self.df_tracks.select_dtypes(include=['object']).columns))

            self.df_feats = FeaturesDf(df_tracks=self.df_tracks,
                                       train_class=self.train_class,
                                       list_path_tracks=tracks_existing_path_list,
                                       config=self.config,
                                       exports_path=self.exports_path,
                                       log_level=self.log_level,
                                       ).create_low_level_df()

            self.y = self.df_tracks[self.train_class].values
            self.logger.info("Features, Labels, and Tracks are exported successfully..")
            return self.df_feats, self.y, self.df_tracks["track"].values
        else:
            self.logger.error("No low-level data found.")
            return None, None, None
