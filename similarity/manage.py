from __future__ import print_function
from flask.cli import FlaskGroup
import click

import webserver
import db
import db.similarity

cli = FlaskGroup(add_default_commands=False, create_app=webserver.create_app_flaskgroup)


@cli.command(name="add-metrics")
@click.option("--batch-size", "-b", type=int, help="Override processing batch size.")
def add_metrics(batch_size=None):
    """Computes all 12 base metrics for each recording
    in the lowlevel table, inserting these values in
    the similarity table."""
    click.echo("Adding all metrics...")
    db.similarity.add_metrics(batch_size=batch_size)
    click.echo("Finished adding all metrics, exiting...")
