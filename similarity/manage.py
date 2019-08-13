from __future__ import print_function
from flask.cli import FlaskGroup
import click

import webserver
import db
import db.similarity
import db.similarity_stats

NORMALIZATION_SAMPLE_SIZE = 10000

cli = FlaskGroup(add_default_commands=False, create_app=webserver.create_app_flaskgroup)


@cli.command(name="add-metrics")
@click.option("--batch-size", "-b", type=int, default=10000, help="Override processing batch size.")
def add_metrics(batch_size):
    """Computes all 12 base metrics for each recording
    in the lowlevel table, inserting these values in
    the similarity.similarity table. 
    
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


@cli.command(name="compute-stats")
@click.option("--force", "-f", default=False, help="Remove existing stats before computing.")
@click.option("--sample-size", "-s", type=int, default=NORMALIZATION_SAMPLE_SIZE, \
    help="Override normalization lowlevel data sample size. \
         Must be >= 1% of lowlevel_json entries.")
def compute_stats(sample_size, force):
    """Computes the mean and standard deviation for 
    lowlevel features that are associated with the
    normalized metrics.

    Stats are computed using a sample of items from the
    lowlevel_json table, configured using `--sample-size`.

    Adds these statistics to the similarity.similarity_stats 
    table with the corresponding metric.

    A list of normalized metrics:
        - MFCCs
        - Weighted MFCCs
        - GFCCs
        - Weighted GFCCs
    """
    click.echo("Computing stats...")
    db.similarity_stats.compute_stats(sample_size, force=force)
    click.echo("Finished!")


@cli.command(name="init")
@click.option("--force", "-f", default=False, help="Remove existing stats before computing.")
@click.option("--sample-size", "-s", type=int, default=NORMALIZATION_SAMPLE_SIZE, \
    help="Override normalization lowlevel data sample size. \
         Must be >= 1% of lowlevel_json entries.")
@click.option("--batch-size", "-b", type=int, default=10000, help="Override processing batch size.")
def init(batch_size, sample_size, force):
    """Initialization command for the similarity engine.
    The following steps will occur:
        1. Compute global stats required for similarity
           using a sample of the lowlevel_json table.
        2. Compute base metrics for all recordings in
           the lowlevel table, inserting these values
           in the similarity.similarity table.

    Options:
        --sample-size: alters sample size when computing stats.
        --batch-size: alters batch size when adding metrics 
        incrementally.
    """
    click.echo("Computing stats...")
    db.similarity_stats.compute_stats(sample_size, force=force)
    click.echo("Finished computing stats. Adding all metrics...")
    db.similarity.add_metrics(batch_size)
    click.echo("Finished adding all metrics, exiting...")
