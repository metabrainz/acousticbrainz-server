import json
import pandas as pd
from ..transformation.utils_preprocessing import flatten_dict_full


def create_low_level_features_df(list_path_tracks, logger):
    """
    Creates the low-level DataFrame. Cleans also the low-level data from the unnecessary features before creating
    the DF.
    Returns:
        The low-level features (pandas DataFrame) from all the tracks in the collection.
    """
    logger.info("---- CREATE LOW LEVEL DATAFRAME ----")

    list_feats_tracks = []
    counter_items_transformed = 0

    for track_low_level_path in list_path_tracks:
        try:
            with open(track_low_level_path) as f:
                data_feats_item = json.load(f, strict=False)
        except Exception:
            logger.error("Exception occurred in loading file:", exc_info=True)
        # remove unnecessary features data
        try:
            if 'beats_position' in data_feats_item['rhythm']:
                del data_feats_item['rhythm']['beats_position']
        except KeyError:
            logger.error("There is no 'rhythm' key in the low level data.", exc_info=True)

        # data dictionary transformed to a fully flattened dictionary
        data_feats_item = flatten_dict_full(data_feats_item)

        # append to a full tracks features pandas df
        list_feats_tracks.append(dict(data_feats_item))

        counter_items_transformed += 1

    # The dictionary's keys list is transformed to type <class 'list'>
    df_feats_tracks = pd.DataFrame(list_feats_tracks, columns=list(list_feats_tracks[0].keys()))
    logger.debug("COLUMNS CONTAIN OBJECTS: \n{}".format(
        df_feats_tracks.select_dtypes(include=['object']).columns))
    logger.info("Exporting low-level data (DataFrame)..")
    return df_feats_tracks

