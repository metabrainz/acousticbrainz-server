from __future__ import print_function

import json
import sys
import os
ROOT_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), "..")
sys.path.append(ROOT_DIR)

from google.cloud import bigquery

import config

def main():
    print("Checking BigQuery tables in dataset {}".format(config.BIGQUERY_DATASET))
    bigquery_client = bigquery.Client()
    dataset = bigquery_client.dataset(config.BIGQUERY_DATASET)

    table = dataset.table(config.BIGQUERY_LL_TABLE)
    if table.exists():
        print("Lowlevel table {} exists.".format(config.BIGQUERY_LL_TABLE))
    else:
        print("Lowlevel table {} doesn't exist, creating...".format(config.BIGQUERY_LL_TABLE))
        schema_file = os.path.join(ROOT_DIR, "admin", "bigquery", "lowlevel-schema.json")
        schema = json.load(open(schema_file))
        schema = bigquery.table._parse_schema_resource({'fields': schema})
        table = dataset.table(config.BIGQUERY_LL_TABLE, schema)
        table.create()
        print("Done.")

    table = dataset.table(config.BIGQUERY_HL_TABLE)
    if table.exists():
        print("Highlevel table {} exists.".format(config.BIGQUERY_HL_TABLE))
    else:
        print("Highlevel table {} doesn't exist, creating...".format(config.BIGQUERY_HL_TABLE))
        schema_file = os.path.join(ROOT_DIR, "admin", "bigquery", "highlevel-schema.json")
        schema = json.load(open(schema_file))
        schema = bigquery.table._parse_schema_resource({'fields': schema})
        table = dataset.table(config.BIGQUERY_HL_TABLE, schema)
        table.create()
        print("Done.")

if __name__ == "__main__":
    main()
