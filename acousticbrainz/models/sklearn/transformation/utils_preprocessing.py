import re
import collections


def flatten_dict_full(dictionary, sep="_"):
    """
    Args:
        dictionary:
        sep:

    Returns:

    """
    obj = collections.OrderedDict()

    def recurse(t, parent_key=""):
        if isinstance(t, list):
            for i in range(len(t)):
                recurse(t[i], parent_key + sep + str(i) if parent_key else str(i))
        elif isinstance(t, dict):
            for k, v in t.items():
                recurse(v, parent_key + sep + k if parent_key else k)
        else:
            obj[parent_key] = t

    recurse(dictionary)

    return obj


def list_descr_handler(descr_list):
    """
    Args:
        descr_list:

    Returns:

    """
    keys_list_handle = []
    for item in descr_list:
        if item.endswith(".*"):
            item = item.replace(".*", "_")
        elif item.startswith("*."):
            item = item.replace("*.", "_")
        else:
            item = item.replace("*", "")
        item = item.replace(".", "_")
        keys_list_handle.append(item)
    return keys_list_handle


def feats_selector_list(df_feats_columns, feats_select_list):
    """
    Args:
        df_feats_columns:
        feats_select_list:

    Returns:

    """
    columns_list = list(df_feats_columns)
    columns_select_list = []
    counter_feats = 0
    for item in feats_select_list:
        for sel_item in columns_list:
            if re.search(item, sel_item):
                columns_select_list.append(sel_item)
                counter_feats += 1
    print("features selected: {}".format(counter_feats))
    return columns_select_list
