import pandas as pd
from termcolor import colored
import collections
import joblib
import os
import six

from sklearn.base import BaseEstimator, TransformerMixin
from ..helper_functions.utils import FindCreateDirectory
from ..transformation.utils_preprocessing import list_descr_handler
from ..transformation.utils_preprocessing import feats_selector_list
from ..helper_functions.logging_tool import LoggerSetup

# avoid the module's method call deprecation
try:
    collectionsAbc = six.moves.collections_abc
except AttributeError:
    collectionsAbc = collections


class TransformPredictions:
    def __init__(self, config, df_feats, process, train_class, exports_path, log_level):
        self.config = config
        self.df_feats = df_feats
        self.process = process
        self.train_class = train_class
        self.exports_path = exports_path
        self.log_level = log_level

        self.logger = ""
        self.list_features = []
        self.feats_cat_list = []
        self.feats_num_list = []

        self.feats_prepared = []

        self.setting_logger()

    def setting_logger(self):
        self.logger = LoggerSetup(config=self.config,
                                  exports_path=self.exports_path,
                                  name="predict_{}".format(self.train_class),
                                  train_class=self.train_class,
                                  mode="a",
                                  level=self.log_level).setup_logger()

    def post_processing(self):
        print(colored("PROCESS: {}".format(self.process), "cyan"))
        # list_preprocesses = []

        self.logger.debug("Track Features - Low Level: {}".format(self.df_feats))
        self.logger.debug("Shape of DF: {}".format(self.df_feats.shape))

        self.list_features = list(self.df_feats.columns)

        exports_dir = self.config.get("exports_directory")
        models_path = FindCreateDirectory(self.exports_path,
                                          os.path.join(exports_dir, "models")).inspect_directory()

        # clean list
        print(colored("Cleaning..", "yellow"))
        cleaning_conf_list = list_descr_handler(self.config["excludedDescriptors"])
        self.logger.debug("cleaning list: {}".format(cleaning_conf_list))
        feats_clean_list = feats_selector_list(self.df_feats.columns, cleaning_conf_list)
        self.list_features = [x for x in self.df_feats.columns if x not in feats_clean_list]
        self.logger.debug("List after cleaning some feats: {}".format(len(self.list_features), "blue"))

        # remove list
        print(colored("Removing unnecessary features..", "yellow"))
        if self.config["processing"][self.process][0]["transfo"] == "remove":
            remove_list = list_descr_handler(self.config["processing"][self.process][0]["params"]["descriptorNames"])
            feats_remove_list = feats_selector_list(self.df_feats.columns, remove_list)
            self.list_features = [x for x in self.list_features if x not in feats_remove_list]
            self.logger.debug("List after removing unnecessary feats: {}".format(len(self.list_features), "blue"))

        # enumerate list
        print(colored("Removing unnecessary features..", "yellow"))
        if self.config["processing"][self.process][1]["transfo"] == "enumerate":
            enumerate_list = list_descr_handler(self.config["processing"][self.process][1]["params"]["descriptorNames"])
            self.feats_cat_list = feats_selector_list(self.list_features, enumerate_list)
            self.logger.debug("Enumerating feats: {}".format(self.feats_cat_list))
            self.feats_num_list = [x for x in self.list_features if x not in self.feats_cat_list]
            self.logger.debug("List Num feats: {}".format(len(self.feats_num_list)))
            self.logger.debug("List Cat feats: {}".format(len(self.feats_cat_list), "blue"))

        # BASIC
        if self.process == "basic":
            print(colored("Process doing: {}".format(self.process), "green"))
            self.logger.debug("List post-Num feats: {}".format(len(self.feats_num_list)))

            # load pipeline
            full_pipeline = joblib.load(os.path.join(models_path, "full_pipeline_{}.pkl".format(self.process)))

            self.feats_prepared = full_pipeline.transform(self.df_feats)

        # LOW-LEVEL or MFCC
        if self.process == "lowlevel" or self.process == "mfcc":
            print(colored("Process doing: {}".format(self.process), "green"))
            sel_list = list_descr_handler(self.config["processing"][self.process][2]["params"]["descriptorNames"])
            self.feats_num_list = feats_selector_list(self.feats_num_list, sel_list)
            self.logger.debug("List post-Num feats: {}".format(len(self.feats_num_list)))

            # load pipeline
            full_pipeline = joblib.load(os.path.join(models_path, "full_pipeline_{}.pkl".format(self.process)))

            self.feats_prepared = full_pipeline.transform(self.df_feats)

        # NOBANDS
        if self.process == "nobands":
            print(colored("Process doing: {}".format(self.process), "green"))
            sel_list = list_descr_handler(self.config["processing"][self.process][2]["params"]["descriptorNames"])
            feats_rem_list = feats_selector_list(self.df_feats, sel_list)
            self.feats_num_list = [x for x in self.feats_num_list if x not in feats_rem_list]
            self.logger.debug("List post-Num feats: {}".format(len(self.feats_num_list)))

            # load pipeline
            full_pipeline = joblib.load(os.path.join(models_path, "full_pipeline_{}.pkl".format(self.process)))

            self.feats_prepared = full_pipeline.transform(self.df_feats)

        # NORMALIZED
        if self.process == "normalized":
            print(colored("Process doing: {}".format(self.process), "green"))
            self.logger.debug("List post-Num feats: {}".format(len(self.feats_num_list)))

            # load pipeline
            full_pipeline = joblib.load(os.path.join(models_path, "full_pipeline_{}.pkl".format(self.process)))

            self.feats_prepared = full_pipeline.transform(self.df_feats)

        # GAUSSIANIZED
        if self.process == "gaussianized":
            print(colored("Process doing: {}".format(self.process), "green"))
            gauss_list = list_descr_handler(self.config["processing"][self.process][3]["params"]["descriptorNames"])
            feats_num_gauss_list = feats_selector_list(self.feats_num_list, gauss_list)
            feats_num_no_gauss_list = [x for x in self.feats_num_list if x not in feats_num_gauss_list]

            self.logger.debug("List post-Num feats: {}".format(len(self.feats_num_list)))
            self.logger.debug("List post-Num-Gauss feats: {}".format(len(feats_num_gauss_list)))

            # load normalization pipeline
            # full_pipeline = joblib.load(os.path.join(exports_dir, "full_pipeline_{}.pkl".format(self.process)))
            full_normalize_pipeline = joblib.load(os.path.join(models_path,
                                                               "full_normalize_pipeline_{}.pkl".format(self.process)))
            # normalize
            self.feats_prepared = full_normalize_pipeline.transform(self.df_feats)

            # transform numpy array to pandas DF for guassianizing
            self.df_feats = pd.DataFrame(data=self.feats_prepared)
            columns = list(self.df_feats.columns)
            # print(columns)
            select_rename_list = columns[:len(self.feats_num_list)]
            select_rename_list = self.feats_num_list
            select_no_rename_list = columns[len(self.feats_num_list):]
            self.logger.debug("Selected no rename list: {}".format(select_no_rename_list))
            new_feats_columns = select_rename_list + select_no_rename_list
            self.df_feats.columns = new_feats_columns
            self.logger.debug("Normalized Features DF:")
            self.logger.debug("\n{}".format(self.df_feats))
            self.logger.debug("Shape: {}".format(self.df_feats.shape))
            # feats_no_gauss_list = [x for x in new_feats_columns if x not in feats_num_gauss_list]

            # load guassianization pipeline
            full_gauss_pipeline = joblib.load(os.path.join(models_path,
                                                           "full_gauss_pipeline_{}.pkl".format(self.process)))

            self.feats_prepared = full_gauss_pipeline.transform(self.df_feats)

        return self.feats_prepared


# Create a class to select numerical or categorical columns
class DataFrameSelector(BaseEstimator, TransformerMixin):
    def __init__(self, attribute_names):
        self.attribute_names = attribute_names

    def fit(self, X, y=None):
        return self

    def transform(self, X):
        return X[self.attribute_names].values
