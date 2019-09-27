from __future__ import print_function
from flask.cli import FlaskGroup
import click

import db.data
import webserver
import similarity.path
from similarity.index_model import AnnoyModel

cli = FlaskGroup(add_default_commands=False, create_app=webserver.create_app_flaskgroup)

@cli.command(name="path")
@click.argument("mbid_1")
@click.option("--offset-1", default=0)
@click.argument("mbid_2")
@click.option("--offset-2", default=0)
def path(mbid_1, offset_1, mbid_2, offset_2):
    metric = "mfccs"
    max_tracks = 100
    # mbid_1 = "13ed6782-8ae1-4fcf-b0c9-9da757412d5d"
    # mbid_1 = "4b5273c8-45f2-4bea-b73c-5128cd57faa8"
    rec_1 = (mbid_1, offset_1)
    # mbid_2 = "4519fc9e-8b9d-45c1-9da4-8ec6688a6ce6"
    # mbid_2 = "62c2e20a-559e-422f-a44c-9afa7882f0c4"
    rec_2 = (mbid_2, offset_2)

    path, distances = similarity.path.get_path(rec_1, rec_2, max_tracks, metric)
    print(path)
    # print(distances)
    print(len(path))
    # index = AnnoyModel(metric, load_existing=True)
    # id = db.data.get_lowlevel_id(mbid_2, offset_2)
    # ids, recs, distances = index.get_nns_by_id(id, 100)
    # print("Distance of nearest neighbours")
    # print(distances)
