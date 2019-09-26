from __future__ import print_function
from flask.cli import FlaskGroup
import click

import webserver
import similarity.path

cli = FlaskGroup(add_default_commands=False, create_app=webserver.create_app_flaskgroup)

@cli.command(name="path")
def path():
    metric = "mfccs"
    max_tracks = 100
    # mbid_1 = "13ed6782-8ae1-4fcf-b0c9-9da757412d5d"
    mbid_1 = "743efbdf-4a38-4c5e-b977-fe1e8ca14b5f"
    offset_1 = 0
    rec_1 = (mbid_1, offset_1)
    # mbid_2 = "4519fc9e-8b9d-45c1-9da4-8ec6688a6ce6"
    mbid_2 = "d695b036-88de-4b13-bdbf-4d46f21d76a7"
    offset_2 = 0
    rec_2 = (mbid_2, offset_2)

    path = similarity.path.get_path(rec_1, rec_2, max_tracks, metric)
    print(path)
