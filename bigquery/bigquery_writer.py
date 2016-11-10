#!/usr/bin/env python

from __future__ import print_function
from __future__ import absolute_import

import sys
import os
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), ".."))
import time
from pprint import pprint
import json

import db
import db.bigquery
import config

from sqlalchemy import text

from google.cloud import bigquery


SLEEP_DURATION = 30  # number of seconds to wait between runs

def main():
    db.init_db_engine(config.SQLALCHEMY_DATABASE_URI)

    bigquery_client = bigquery.Client()
    dataset = bigquery_client.dataset(config.BIGQUERY_DATASET)
    lltable = dataset.table(config.BIGQUERY_LL_TABLE)
    lltable.reload()
    hltable = dataset.table(config.BIGQUERY_HL_TABLE)
    hltable.reload()

    while True:
        lowlevel_items = db.bigquery.get_lowlevel_documents()
        highlevel_items = db.bigquery.get_highlevel_documents()

        if len(lowlevel_items) == 0 and len(highlevel_items) == 0:
            print("No items remaining to process, sleeping.")
            time.sleep(SLEEP_DURATION)
        else:
            if lowlevel_items:
                rowids = []
                docs = []
                for rowid, gid, data in lowlevel_items:
                    docs.append(translate_lowlevel(gid, rowid, data))
                    rowids.append(rowid)
                errors = lltable.insert_data(docs)

                if not errors:
                    plural = "" if len(lowlevel_items) == 1 else "s"
                    print('Loaded {} row{} into {}:{}'.format(len(lowlevel_items), plural, config.BIGQUERY_DATASET, config.BIGQUERY_LL_TABLE))
                    db.bigquery.add_lowlevel_upload_records(rowids)
                else:
                    print('lowlevel Errors:')
                    pprint(errors)

            if highlevel_items:
                rowids = []
                docs = []
                for rowid, gid, data in highlevel_items:
                    docs.append(translate_highlevel(gid, str(rowid), data))
                    rowids.append(rowid)
                errors = hltable.insert_data(docs)

                if not errors:
                    plural = "" if len(highlevel_items) == 1 else "s"
                    print('Loaded {} row{} into {}:{}'.format(len(highlevel_items), plural, config.BIGQUERY_DATASET, config.BIGQUERY_HL_TABLE))
                    db.bigquery.add_highlevel_upload_records(rowids)
                else:
                    print('highlevel Errors:')
                    pprint(errors)


def translate_lowlevel(gid, offset, data):
    """ Convert lowlevel data into a format that can be uploaded to bigquery
        - Change list-of-lists to list-of-dicts
        - Remove metadata tag names with spaces in them
        - Add mbid and offset top level data
    """
    def _transform(data):
        return [{"dimension": "%s" % dim, "values": vals} for dim, vals in enumerate(data, 1)]

    data["meta"] = {"gid": gid, "offset": "%s" % offset}
    data["lowlevel"]["mfcc"]["cov"] = _transform(data["lowlevel"]["mfcc"]["cov"])
    data["lowlevel"]["mfcc"]["icov"] = _transform(data["lowlevel"]["mfcc"]["icov"])
    data["lowlevel"]["gfcc"]["cov"] = _transform(data["lowlevel"]["gfcc"]["cov"])
    data["lowlevel"]["gfcc"]["icov"] = _transform(data["lowlevel"]["gfcc"]["icov"])

    for t, v in data["metadata"]["tags"].items():
        if " " in t:
            del data["metadata"]["tags"][t]

    return [data["meta"], data["lowlevel"], data["tonal"], data["rhythm"], data["metadata"]]


def translate_highlevel(gid, offset, data):
    """ Convert highlevel data into a format that can be uploaded to bigquery
        - Split multiple models into one record per model
        - Remove metadata tag names with spaces in them
        - Add mbid and offset top level data
    """

    ret = {"highlevel": {}, "metadata": data["metadata"], "meta": {"gid": gid, "offset": "%s" % offset}}
    # TODO: should only be one item here, or we return a list
    for model, results in data["highlevel"].items():
        item = {"version": results["version"],
                "probability": results["probability"],
                "value": results["value"],
                "model": model,
                "results": []}
        for k, v in results["all"].items():
            item["results"].append({"value": k, "probability": v})
        ret["highlevel"] = item

    for t, v in ret["metadata"]["tags"].items():
        if " " in t:
            del ret["metadata"]["tags"][t]

    return [ret["meta"], ret["highlevel"], ret["metadata"]]


if __name__ == "__main__":
    main()
