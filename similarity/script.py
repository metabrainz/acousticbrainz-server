from __future__ import print_function
from flask.cli import FlaskGroup
import timeit
import time
import click

import webserver
import db

from utils import get_all_metrics, get_all_indices
from index_model import AnnoyModel

from sqlalchemy import text
from collections import defaultdict

PROCESS_BATCH_SIZE = 10000

cli = FlaskGroup(add_default_commands=False, create_app=webserver.create_app_flaskgroup)

mbids=[
    'ebf79ba5-085e-48d2-9eb8-2d992fbf0f6d',
    '8d5f76cf-0fa1-45a1-8464-68053d03b46b',
    'c718f7c1-b63b-4638-bda3-42ca56177dd7',
    '47974dfd-f37d-4f41-b952-18a86af009d2',
    '0cdc9b5b-b16b-4ff1-9f16-5b4ba76f1c17',
    'b7ffa922-7bb8-4703-aa51-3bcc6d9cc364'
]


@cli.command(name='probe-annoy')
def probe_annoy():
    """Get similar recordings using the annoy index."""
    with db.engine.connect() as connection:
        index = AnnoyModel(connection, "mfccs", load_existing=True)
        recordings = index.get_nns_by_mbid(mbids[0], 0, 1000)

        # print("Similar recordings:")
        # print(recordings)
        # print("========================")
        # query = text("""
        #     SELECT gid
        #     FROM lowlevel
        #     WHERE id
        #     IN :recordings
        # """)
        # result = connection.execute(query, { "recordings": tuple(recordings) })

        # recordings = []
        # for row in result.fetchall():
        #     recordings.append(row["gid"])
        # print("Similar recordings:")
        # print(recordings)
        # print("===================")
        ret = []
        for mbid, offset in recordings:
            ret.append(mbid)

        print(ret)
        return ret
