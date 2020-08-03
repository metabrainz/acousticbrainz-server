import pandas as pd
from termcolor import colored
import collections
import joblib
import os

from utils import FindCreateDirectory
from transformation.utils_preprocessing import list_descr_handler
from transformation.utils_preprocessing import feats_selector_list
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.preprocessing import OneHotEncoder, MinMaxScaler, QuantileTransformer
from sklearn.pipeline import FeatureUnion
from sklearn.pipeline import Pipeline
from logging_tool import LoggerSetup


# avoid the module's method call deprecation
try:
    collectionsAbc = collections.abc
except AttributeError:
    collectionsAbc = collections


class Transform:
    def __init__(self, config, df_feats, process, train_class, exports_path, log_level):
        self.config = config
        self.df_feats = df_feats
        self.process = process
        self.train_class = train_class
        self.exports_path = exports_path
        self.log_level = log_level

        self.list_features = []
        self.feats_cat_list = []
        self.feats_num_list = []
        self.df_cat = pd.DataFrame()
        self.df_num = pd.DataFrame()

        self.feats_prepared = []
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

    def post_processing(self):
        print(colored("PROCESS: {}".format(self.process), "cyan"))
        self.logger.debug("PROCESS: {}".format(self.process))
        self.logger.debug("Process: {}".format(self.config["processing"][self.process]))
        # list_preprocesses = []

        self.list_features = list(self.df_feats.columns)

        exports_dir = "{}_{}".format(self.config.get("exports_directory"), self.train_class)
        models_path = FindCreateDirectory(self.exports_path,
                                          os.path.join(exports_dir, "models")).inspect_directory()

        # clean list
        print(colored("Cleaning..", "yellow"))
        self.logger.info("Cleaning..")
        cleaning_conf_list = list_descr_handler(self.config["excludedDescriptors"])
        feats_clean_list = feats_selector_list(self.df_feats.columns, cleaning_conf_list)
        self.list_features = [x for x in self.df_feats.columns if x not in feats_clean_list]
        self.logger.debug("List after cleaning some feats: {}".format(len(self.list_features)))

        # remove list
        print(colored("Removing unnecessary features..", "yellow"))
        self.logger.info("Removing unnecessary features..")
        if self.config["processing"][self.process][0]["transfo"] == "remove":
            remove_list = list_descr_handler(self.config["processing"][self.process][0]["params"]["descriptorNames"])
            feats_remove_list = feats_selector_list(self.df_feats.columns, remove_list)
            self.list_features = [x for x in self.list_features if x not in feats_remove_list]
            self.logger.debug("List after removing unnecessary feats: {}".format(len(self.list_features)))

        # enumerate list
        print(colored("Split numerical / categorical features..", "yellow"))
        if self.config["processing"][self.process][1]["transfo"] == "enumerate":
            enumerate_list = list_descr_handler(self.config["processing"][self.process][1]["params"]["descriptorNames"])
            self.feats_cat_list = feats_selector_list(self.list_features, enumerate_list)
            self.logger.debug("Enumerating feats: {}".format(self.feats_cat_list))
            self.feats_num_list = [x for x in self.list_features if x not in self.feats_cat_list]
            self.logger.debug("List Num feats: {}".format(len(self.feats_num_list)))
            self.logger.debug("List Cat feats: {}".format(len(self.feats_cat_list), "blue"))

        # BASIC
        if self.process == "basic":
            self.logger.debug("List post-Num feats: {}".format(len(self.feats_num_list)))

            num_pipeline = Pipeline([
                ('selector', DataFrameSelector(self.feats_num_list))
            ])

            cat_pipeline = Pipeline([
                ('selector', DataFrameSelector(self.feats_cat_list)),
                ('cat_encoder', OneHotEncoder(handle_unknown='ignore', sparse=False))
            ])

            full_pipeline = FeatureUnion(transformer_list=[
                ("num_pipeline", num_pipeline),
                ("cat_pipeline", cat_pipeline)
            ])

            self.feats_prepared = full_pipeline.fit_transform(self.df_feats)

            # save pipeline
            joblib.dump(full_pipeline, os.path.join(models_path, "full_pipeline_{}.pkl".format(self.process)))

        # LOW-LEVEL or MFCC
        if self.process == "lowlevel" or self.process == "mfcc":
            sel_list = list_descr_handler(self.config["processing"][self.process][2]["params"]["descriptorNames"])
            self.feats_num_list = feats_selector_list(self.feats_num_list, sel_list)
            self.logger.debug("List post-Num feats: {}".format(len(self.feats_num_list)))

            num_pipeline = Pipeline([
                ('selector', DataFrameSelector(self.feats_num_list))
            ])

            cat_pipeline = Pipeline([
                ('selector', DataFrameSelector(self.feats_cat_list)),
                ('cat_encoder', OneHotEncoder(handle_unknown='ignore', sparse=False))
            ])

            full_pipeline = FeatureUnion(transformer_list=[
                ("num_pipeline", num_pipeline),
                ("cat_pipeline", cat_pipeline)
            ])

            self.feats_prepared = full_pipeline.fit_transform(self.df_feats)

            # save pipeline
            joblib.dump(full_pipeline, os.path.join(models_path, "full_pipeline_{}.pkl".format(self.process)))

        # NOBANDS
        if self.process == "nobands":
            sel_list = list_descr_handler(self.config["processing"][self.process][2]["params"]["descriptorNames"])
            feats_rem_list = feats_selector_list(self.df_feats, sel_list)
            self.feats_num_list = [x for x in self.feats_num_list if x not in feats_rem_list]
            self.logger.debug("List post-Num feats: {}".format(len(self.feats_num_list)))

            num_pipeline = Pipeline([
                ('selector', DataFrameSelector(self.feats_num_list))
            ])

            cat_pipeline = Pipeline([
                ('selector', DataFrameSelector(self.feats_cat_list)),
                ('cat_encoder', OneHotEncoder(handle_unknown='ignore', sparse=False))
            ])

            full_pipeline = FeatureUnion(transformer_list=[
                ("num_pipeline", num_pipeline),
                ("cat_pipeline", cat_pipeline)
            ])

            self.feats_prepared = full_pipeline.fit_transform(self.df_feats)

            # save pipeline
            joblib.dump(full_pipeline, os.path.join(models_path, "full_pipeline_{}.pkl".format(self.process)))

        # NORMALIZED
        if self.process == "normalized":
            self.logger.debug("List post-Num feats: {}".format(len(self.feats_num_list)))
            num_pipeline = Pipeline([
                ('selector', DataFrameSelector(self.feats_num_list)),
                ('minmax_scaler', MinMaxScaler()),
            ])

            cat_pipeline = Pipeline([
                ('selector', DataFrameSelector(self.feats_cat_list)),
                ('cat_encoder', OneHotEncoder(handle_unknown='ignore', sparse=False))
            ])

            full_pipeline = FeatureUnion(transformer_list=[
                ("num_pipeline", num_pipeline),
                ("cat_pipeline", cat_pipeline)
            ])

            self.feats_prepared = full_pipeline.fit_transform(self.df_feats)

            # save pipeline
            joblib.dump(full_pipeline, os.path.join(models_path, "full_pipeline_{}.pkl".format(self.process)))

        # GAUSSIANIZED
        if self.process == "gaussianized":
            gauss_list = list_descr_handler(self.config["processing"][self.process][3]["params"]["descriptorNames"])
            feats_num_gauss_list = feats_selector_list(self.feats_num_list, gauss_list)
            feats_num_no_gauss_list = [x for x in self.feats_num_list if x not in feats_num_gauss_list]

            self.logger.debug("List post-Num feats: {}".format(len(self.feats_num_list)))
            self.logger.debug("List post-Num-Gauss feats: {}".format(len(feats_num_gauss_list)))
            self.logger.debug("List post-Num-No-Gauss feats: {}".format(len(feats_num_no_gauss_list)))

            num_norm_pipeline = Pipeline([
                ("selector_num", DataFrameSelector(self.feats_num_list)),
                ("minmax_scaler", MinMaxScaler())
            ])

            cat_pipeline = Pipeline([
                ('selector', DataFrameSelector(self.feats_cat_list)),
                ('cat_encoder', OneHotEncoder(handle_unknown='ignore', sparse=False))
            ])

            full_normalize_pipeline = FeatureUnion(transformer_list=[
                ("num_pipeline", num_norm_pipeline),
                ("cat_pipeline", cat_pipeline)
            ])

            self.feats_prepared = full_normalize_pipeline.fit_transform(self.df_feats)
            self.logger.debug("Feats prepared normalized shape: {}".format(self.feats_prepared.shape))
            # save pipeline
            joblib.dump(full_normalize_pipeline,
                        os.path.join(models_path, "full_normalize_pipeline_{}.pkl".format(self.process)))
            self.df_feats = pd.DataFrame(data=self.feats_prepared)
            columns = list(self.df_feats.columns)
            # print(columns)
            select_rename_list = columns[:len(self.feats_num_list)]
            select_rename_list = self.feats_num_list
            select_no_rename_list = columns[len(self.feats_num_list):]
            print(select_no_rename_list)
            new_feats_columns = select_rename_list + select_no_rename_list
            self.df_feats.columns = new_feats_columns
            self.logger.debug("Normalized Features DF:")
            self.logger.debug("\n{}".format(self.df_feats))
            self.logger.debug("Shape: {}".format(self.df_feats.shape))

            feats_no_gauss_list = [x for x in new_feats_columns if x not in feats_num_gauss_list]

            num_gauss_pipeline = Pipeline([
                ("gauss_sel_num", DataFrameSelector(feats_num_gauss_list)),
                ("gauss_scaler", QuantileTransformer(n_quantiles=1000))
            ])

            num_no_gauss_pipeline = Pipeline([
                ("gauss_sel_num", DataFrameSelector(feats_no_gauss_list))
            ])

            full_gauss_pipeline = FeatureUnion(transformer_list=[
                ("num_gauss_pipeline", num_gauss_pipeline),
                ("num_no_gauss_pipeline", num_no_gauss_pipeline)
            ])

            self.feats_prepared = full_gauss_pipeline.fit_transform(self.df_feats)

            # save pipeline
            joblib.dump(full_gauss_pipeline,
                        os.path.join(models_path, "full_gauss_pipeline_{}.pkl".format(self.process)))

        return self.feats_prepared


# Create a class to select numerical or categorical columns
class DataFrameSelector(BaseEstimator, TransformerMixin):
    def __init__(self, attribute_names):
        self.attribute_names = attribute_names

    def fit(self, X, y=None):
        return self

    def transform(self, X):
        return X[self.attribute_names].values