from __future__ import print_function
from flask.cli import FlaskGroup
import timeit
import time
import click

import webserver
import db

from utils import get_all_metrics, get_all_indices, get_similar_recordings
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


@cli.command(name='probe-postgres')
def probe_postgres():
    """Get similar recordings using the postgres cube index."""
    print("Probing endpoint for postgres...")
    metrics_dict = get_all_metrics()
    print("====================")
    # for mbid in mbids:
    #     for category, metric_list in metrics_dict.items():
    #         for metric, _ in metric_list:
    #             # time = timeit.timeit("get_similar_recordings('{}', '{}')".format(mbid, metric),
    #             #                      setup='from similarity.api import get_similar_recordings',
    #             #                      number=1)
    #             recordings, category, description = get_similar_recordings(mbid, metric)
    #             print(mbid, metric, category, description)
    #             print("Similar recordings:")
    #             print(recordings)
    #             print("===================")
    recordings, category, description = get_similar_recordings(mbids[0], 'mfccs')
    print("Similar recordings:")
    print(recordings)
    print("===================")

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


@cli.command(name='probe-all')
def probe_all():
    metrics_dict = get_all_metrics()
    # Compute similarity for postgres
    click.echo("Pre-computing similarity with Postgres...")
    postgres_similarity = defaultdict(lambda: defaultdict(dict))
    for category, metric_list in metrics_dict.items():
        for metric, _ in metric_list:
            with db.engine.connect() as connection:
                for mbid in mbids:
                    # Time Postgres
                    print("querying postgres...")
                    start = time.time()
                    postgres_recordings, category, description = get_similar_recordings(mbid, metric)
                    end = time.time()
                    postgres_time = end - start
                    print(postgres_time)
                    print("postgres_recordings:")
                    print(postgres_recordings)
                    print("==================================")
                    postgres_similarity[metric][mbid]["recordings"] = ["postgres_recordings"]
                    postgres_similarity[metric][mbid]["time"] = postgres_time

    index_dict = get_all_indices()
    # Compute similarity for annoy
    click.echo("Computing similarity for Annoy...")
    for distance_type in index_dict:
        print("{}".format(distance_type))
        for metric, n_trees in index_dict[distance_type]:
            print("---------------------------")
            print("METRIC: {}".format(metric))
            with db.engine.connect() as connection:
                index = AnnoyModel(connection, metric, n_trees=n_trees, distance_type=distance_type, load_existing=True)
                for mbid in mbids:
                    # Time Annoy
                    start = time.time()
                    annoy_recordings = index.get_nns_by_mbid(mbid, 0, 1000)
                    end = time.time()
                    annoy_time = end - start

                    # Find intersection of solutions
                    postgres_recordings = postgres_similarity[metric][mbid]["recordings"]
                    postgres_time = postgres_similarity[metric][mbid]["time"]
                    intersected_recordings = [recording for recording in annoy_recordings if recording in postgres_recordings]
                    click.echo("{}: Annoy {}, Postgres {}, Number of Intersections {}".format(mbid, annoy_time, postgres_time, len(intersected_recordings)))
