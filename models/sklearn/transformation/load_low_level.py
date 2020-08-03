import os
import json
import pandas as pd
from transformation.utils_preprocessing import flatten_dict_full
from logging_tool import LoggerSetup


class FeaturesDf:
    """
    Features DataFrame object by the JSON low-level data.
     Attributes:
            df_tracks (Pandas DataFrame): The tracks DataFrame that contains the track name, track low-level path,
                                        label, etc.
    """
    def __init__(self, df_tracks, train_class, path_low_level, config, exports_path, log_level):
        self.df_tracks = df_tracks
        self.train_class = train_class
        self.path_low_level = path_low_level
        self.config = config
        self.exports_path = exports_path
        self.log_level = log_level
        self.list_feats_tracks = []
        self.counter_items_transformed = 0
        self.df_feats_tracks = pd.DataFrame()
        self.df_feats_label = pd.DataFrame()

        self.logger = ""

        self.setting_logger()

    def setting_logger(self):
        # set up logger
        self.logger = LoggerSetup(config=self.config,
                                  exports_path=self.exports_path,
                                  name="dataset_exports_transformations_{}".format(self.train_class),
                                  train_class=self.train_class,
                                  mode="a",
                                  level=self.log_level).setup_logger()

    def create_low_level_df(self):
        """
        Creates the low-level DataFrame. Cleans also the low-level data from the unnecessary features before creating
        the DF.

        :return:
        DataFrame: low-level features Daa=taFrame from all the tracks in the collection.
        """
        self.logger.info("---- CREATE LOW LEVEL DATAFRAME ----")
        # clear the list if it not empty
        self.list_feats_tracks.clear()
        for index, row in self.df_tracks.iterrows():
            path_low_data = os.path.join(self.path_low_level, "{}.json".format(row["track"]))
            try:
                f = open(path_low_data)
                data_feats_item = json.load(f, strict=False)
            except Exception as e:
                print("Exception occurred in loading file:", e)
                self.logger.warning("Exception occurred in loading file: {}".format(e))
            # remove unnecessary features data
            try:
                if 'beats_position' in data_feats_item['rhythm']:
                    del data_feats_item['rhythm']['beats_position']
            except Exception as e:
                print("There is no 'rhythm' key in the low level data. Exception:", e)

            # data dictionary transformed to a fully flattened dictionary
            data_feats_item = flatten_dict_full(data_feats_item)

            # append to a full tracks features pandas df
            self.list_feats_tracks.append(dict(data_feats_item))

            self.counter_items_transformed += 1

        # The dictionary's keys list is transformed to type <class 'list'>
        self.df_feats_tracks = pd.DataFrame(self.list_feats_tracks, columns=list(self.list_feats_tracks[0].keys()))
        self.logger.info("COLUMNS CONTAIN OBJECTS: \n{}".format(
            self.df_feats_tracks.select_dtypes(include=['object']).columns))
        self.logger.info("Exporting low-level data (dataframe)")
        return self.df_feats_tracks

    def check_processing_info(self):
        """
        Prints some information about the low-level data to DataFrame transformation step and its middle processes.
        :return:
        """
        self.logger.info('Items parsed and transformed: {}'.format(self.counter_items_transformed))
        # The type of the dictionary's keys list is: <class 'dict_keys'>
        self.logger.info('Type of the list of features keys: {}'.format(type(self.list_feats_tracks[0].keys())))
        # The dictionary's keys list is transformed to type <class 'list'>
        self.logger.info('Confirm the type of list transformation of features keys: {}'
                         .format(type(list(self.list_feats_tracks[0].keys()))))

    def export_tracks_feats_df(self):
        """
        :return:
        DataFrame: The tracks with all the ground truth data and the corresponding low-level data flattened.
        """
        self.logger.info("Concatenating the tracks/labels data DataFrame with the features DataFrame.")
        self.logger.info("TRACKS SHAPE: {}".format(self.df_tracks.shape))
        self.logger.info("LOW LEVEL: {}".format(self.df_feats_tracks.shape))

        self.df_feats_label = pd.concat([self.df_tracks, self.df_feats_tracks], axis=1)
        self.logger.info("FULL: {}".format(self.df_feats_label.shape))
        self.logger.info("COLUMNS CONTAIN OBJECTS: {}"
                         .format(self.df_feats_label.select_dtypes(include=['object']).columns))
        return self.df_feats_label
