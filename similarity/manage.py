from __future__ import print_function
from flask.cli import FlaskGroup
import click

import webserver
import db
import db.similarity

cli = FlaskGroup(add_default_commands=False, create_app=webserver.create_app_flaskgroup)


@cli.command(name="add-metrics")
@click.option("--batch-size", "-b", type=int, default=10000, help="Override processing batch size.")
def add_metrics(batch_size):
    """Computes all 12 base metrics for each recording
    in the lowlevel table, inserting these values in
    the similarity table. 
    
    Requires fetching lowlevel data and the highlevel 
    models for each recording.
    
    Args: 
        batch_size: integer, number of recordings that 
        should be added on each iteration. 
        Suggested value between 10 000 and 20 000.
    """
    click.echo("Adding all metrics...")
    db.similarity.add_metrics(batch_size)
    click.echo("Finished adding all metrics, exiting...")
