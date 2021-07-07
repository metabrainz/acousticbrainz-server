import os
import yaml
import pandas as pd
from termcolor import colored
import random
from ..helper_functions.utils import create_directory
from ..transformation.load_low_level import FeaturesDf


def load_local_ground_truth(gt_filename):
    """ Loads the the ground truth file.

    The Ground Truth data which contains the tracks and the corresponding
    labels they belong to. The path to the related tracks' low-level data
    (features in JSON format) can be extracted from this file too.
    """
    with open(gt_filename, "r") as stream:
        try:
            ground_truth_data = yaml.safe_load(stream)
            print("Ground truth file loaded.")
            return ground_truth_data
        except yaml.YAMLError as exc:
            print("Error in loading the ground truth file.")
            print(exc)


def export_gt_tracks(ground_truth_data, seed):
    """
    It takes a dictionary of the tracks from the groundtruth and it transforms it
    to a list of tuples (track, label). Then it shuffles the list based on the seed
    specified in the configuration file, and returns that shuffled list.

    Returns:
        A list of tuples with the tracks and their corresponding labels.
    """
    labeled_tracks = ground_truth_data["groundTruth"]
    tracks_list = []
    for track, label in labeled_tracks.items():
        tracks_list.append((track, label))
    print(colored("SEED is set to: {}".format(seed, "cyan")))
    random.seed(a=seed)
    random.shuffle(tracks_list)
    print("Listed tracks in GT file: {}".format(len(tracks_list)))
    return tracks_list


def create_df_tracks(config, tracks_list, train_class, exports_path, logger):
    """
    TODO: Description
    Returns:
        TODO: Description
    """

    logger.info("---- EXPORTING FEATURES - LABELS - TRACKS ----")
    dataset_dir = config.get("dataset_dir")
    print('DATASET-DIR', dataset_dir)
    dirpath = os.path.join(os.getcwd(), dataset_dir)
    low_level_list = list()
    for (dirpath, dirnames, filenames) in os.walk(dirpath):
        low_level_list += [os.path.join(dirpath, file) for file in filenames if file.endswith(".json")]
    if len(low_level_list) != 0:
        logger.info("Low-level features for the tracks found.")
        # processing the names of the tracks that are inside both the GT file and the low-level json files
        # list with the tracks that are included in the low-level json files
        tracks_existing_list = [e for e in tracks_list for i in low_level_list if e[0] in i]
        # list with the low-level json tracks' paths that are included in tracks list
        tracks_existing_path_list = [i for e in tracks_list for i in low_level_list if e[0] in i]
        logger.debug("tracks existed found: {}".format(len(tracks_existing_list)))
        logger.debug("tracks_path existed found: {}".format(len(tracks_existing_path_list)))
        logger.debug("{}".format(tracks_existing_list[:4]))
        logger.debug("{}".format(tracks_existing_path_list[:4]))
        logger.debug("The founded tracks tracks listed successfully.")
        logger.debug("Generate random number within a given range of listed tracks:")
        # Random number between 0 and length of listed tracks
        random_num = random.randrange(len(tracks_existing_list))
        logger.debug("Check if the tracks are the same in the same random index in both lists")
        logger.debug("{}".format(tracks_existing_list[random_num]))
        logger.debug("{}".format(tracks_existing_path_list[random_num]))

        tracks_list = tracks_existing_list
        # create the dataframe with tracks that are bothe in low-level files and the GT file
        df_tracks = pd.DataFrame(data=tracks_list, columns=["track", train_class])
        logger.debug("Shape of tracks DF created before cleaning: {}".format(df_tracks.shape))
        logger.debug("Check the shape of a temporary DF that includes if there are any NULL values:")
        logger.debug("{}".format(df_tracks[df_tracks.isnull().any(axis=1)].shape))

        logger.debug("Drop rows with NULL values if they exist..")
        if df_tracks[df_tracks.isnull().any(axis=1)].shape[0] != 0:
            df_tracks.dropna(inplace=True)
            logger.debug("Check if there are NULL values after the cleaning process:")
            logger.debug("{}".format(df_tracks[df_tracks.isnull().any(axis=1)].shape))
            logger.debug("Re-index the tracks DF..")
            df_tracks = df_tracks.reset_index(drop=True)
        else:
            logger.info("There are no NULL values found.")

        # export shuffled tracks to CSV format
        tracks_path = create_directory(exports_path, "tracks_csv_format")
        df_tracks.to_csv(os.path.join(tracks_path, "tracks_{}_shuffled.csv".format(train_class)))
        logger.debug("DF INFO:")
        logger.debug("{}".format(df_tracks.info()))
        logger.debug("COLUMNS CONTAIN OBJECTS: {}".format(
            df_tracks.select_dtypes(include=['object']).columns))

        df_feats = FeaturesDf(df_tracks=df_tracks,
                              train_class=train_class,
                              list_path_tracks=tracks_existing_path_list,
                              config=config,
                              exports_path=exports_path,
                              logger=logger
                              ).create_low_level_df()

        y = df_tracks[train_class].values
        logger.info("Features, Labels, and Tracks are exported successfully..")
        return df_feats, y, df_tracks["track"].values
    else:
        logger.error("No low-level data found.")
        return None, None, None
