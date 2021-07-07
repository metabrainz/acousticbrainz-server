import os
import json
import numpy as np
from ..classification.confusion_matrix_export import load_as_confusion_matrix


def matrix_creation(classes, tracks, y_actual, y_hat, logger, export_save_path, export_name):
    logger.info("MATRIX DICTIONARY CREATION")
    # classes numpy array to list conversion
    logger.info("CLASSES BEFORE CONVERSION {}".format(type(classes)))
    classes = classes.tolist()
    logger.info("CLASSES AFTER CONVERSION: {}".format(type(classes)))
    logger.info("CLASSES: {}".format(classes))
    matrix_dict = {}
    # print(type(y_actual))
    # print(type(y_hat))
    for pred_class in classes:
        logger.info("Class process: {}".format(pred_class))
        # print("Class type:", type(pred_class))
        # pred_class = str(pred_class)
        class_item_dict = {}
        for track, actual, pred in zip(tracks, y_actual, y_hat):
            if isinstance(actual, (int, np.int64)):
                actual = int(actual)
            if isinstance(pred, (int, np.int64)):
                pred = int(pred)
            if pred_class == actual == pred:
                if actual not in class_item_dict:
                    class_item_dict[actual] = []
                class_item_dict[actual].append(track)
            elif pred_class == actual and actual != pred:
                if pred not in class_item_dict:
                    class_item_dict[pred] = []
                class_item_dict[pred].append(track)
        matrix_dict[pred_class] = class_item_dict
    logger.info("Matrix classified..")
    matrix_general_dict = {"matrix": matrix_dict}
    logger.debug("The whole matrix dictionary:\n{}".format(matrix_general_dict))

    # Serializing json
    json_object = json.dumps(matrix_general_dict, indent=4)
    # Writing to sample.json
    load_file_path = os.path.join(export_save_path, export_name)
    with open(load_file_path, "w") as outfile:
        outfile.write(json_object)
    logger.info("Best results matrix stored successfully.")

    return matrix_general_dict


def simplified_matrix_export(best_result_file, logger, export_save_path, export_name, write_mode=False):
    load_file_path = os.path.join(export_save_path, best_result_file)
    # best model data load from JSON
    logger.info("load best model results from JSON format file")
    confusion_matrix = load_as_confusion_matrix(load_file_path)
    logger.info("Best model results loaded..")
    simplified_cm = {}
    for key, val in confusion_matrix.items():
        simplified_cm[key] = {}
        for predicted_key, predicted_val in val.items():
            simplified_cm[key][predicted_key] = len(predicted_val)
    # export simplified matrix to JSON file
    if write_mode is True:
        # Serializing json
        json_object = json.dumps(simplified_cm, indent=4)
        # Writing to sample.json
        load_file_path = os.path.join(export_save_path, export_name)
        with open(load_file_path, "w") as outfile:
            outfile.write(json_object)
        logger.info("Best simplified matrix stored successfully.")

    return simplified_cm
