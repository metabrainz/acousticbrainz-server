from __future__ import print_function
from flask.cli import FlaskGroup
import click

import webserver
import metrics
from index_model import AnnoyModel
import similarity.utils
import db
import db.similarity

cli = FlaskGroup(add_default_commands=False, create_app=webserver.create_app_flaskgroup)


@cli.command(name="add-metrics")
@click.option("--force", "-f", is_flag=True, help="Recompute existing metrics.")
@click.option("--batch-size", "-b", type=int, help="Override processing batch size.")
def add_metrics(force=False, batch_size=None):
    """Computes all 12 base metrics for each recording
    in the lowlevel table, inserting these values in
    the similarity table."""
    click.echo("Adding all metrics...")
    db.similarity.add_metrics(force=force, batch_size=batch_size)
    click.echo("Finished adding all metrics, exiting...")


@cli.command(name="delete-metric")
@click.argument("metric")
@click.option("--soft", "-s", is_flag=True, help="Don't delete data.")
@click.option("--leave-stats", "-l", is_flag=True, help="Don't delete computed statistics.")
def delete_metric(name, soft=False, leave_stats=False):
    """Deletes the metric specified by the `metric` argument."""
    try:
        metric_cls = metrics.BASE_METRICS[metric]
    except KeyError:
        click.echo('No such metric is implemented: {}'.format(metric))
        return

    with db.engine.begin() as connection:
        metric = metric_cls(connection)
        metric.delete(soft=soft)

        if not leave_stats:
            try:
                metric.delete_stats()
            except AttributeError:
                pass


@cli.command(name='add-index')
@click.argument("metric")
@click.option("--batch_size", "-b", type=int, default=None, help="Size of batches")
@click.option("--n_trees", "-n", type=int, default=10, help="Number of trees for building index. \
                                                            Tradeoff: more trees gives more precision, \
                                                            but takes longer to build.")
@click.option("--distance_type", "-d", default='angular', help="Method of measuring distance between metric vectors")
def add_index(metric, batch_size=None, n_trees=10, distance_type='angular'):
    """Creates an annoy index for the specified metric, adds all recordings to the index."""
    db.similarity.add_index(metric, batch_size=batch_size, n_trees=n_trees, distance_type=distance_type)
    click.echo("Done!")


@cli.command(name='add-indices')
@click.option("--n-trees", "-n", type=int, default=10, help="Number of trees for building index. \
                                                            Tradeoff: more trees gives more precision, \
                                                            but takes longer to build.")
@click.option("--distance-type", "-d", default='angular')
def add_indices(n_trees=10, distance_type='angular'):
    """Creates an annoy index then adds all recordings to the index,
    for each of the base metrics."""
    metrics = ["mfccs",
               "mfccsw",
               "gfccs",
               "gfccsw",
               "key",
               "bpm",
               "onsetrate",
               "moods",
               "instruments",
               "dortmund",
               "rosamerica",
               "tzanetakis"]

    for metric in metrics:
        click.echo("Adding index: {}".format(metric))
        db.similarity.add_index(metric, batch_size=None, n_trees=n_trees, distance_type=distance_type)
    click.echo("Finished.")


@cli.command(name='remove-index')
@click.argument("metric")
@click.option("--n_trees", "-n", type=int, default=10, help="Number of trees for building index. \
                                                            Tradeoff: more trees gives more precision, \
                                                            but takes longer to build.")
@click.option("--distance_type", "-d", default='angular', help="Method of measuring distance between metric vectors.")
def remove_index(metric, n_trees=10, distance_type='angular'):
    """Removes the index with the specified parameters, if it exists.

        Note that each index is built with a distinct number of trees,
        metric, and distance type.
    """
    click.echo("Removing index: {}".format(metric))
    similarity.utils.remove_index(metric, n_trees=n_trees, distance_type=distance_type)
    click.echo("Finished.")


@cli.command(name='remove-indices')
@click.option("--n_trees", "-n", type=int, default=10, help="Number of trees for building index. \
                                                            Tradeoff: more trees gives more precision, \
                                                            but takes longer to build.")
@click.option("--distance_type", "-d", default='angular', help="Method of measuring distance between metric vectors.")
def remove_indices(n_trees=10, distance_type='angular'):
    """Removes indices for each of the following metrics, if they
    exist with the specified parameters."""
    metrics = ["mfccs",
               "mfccsw",
               "gfccs",
               "gfccsw",
               "key",
               "bpm",
               "onsetrate",
               "moods",
               "instruments",
               "dortmund",
               "rosamerica",
               "tzanetakis"]

    for metric in metrics:
        click.echo("Removing index: {}".format(metric))
        similarity.utils.remove_index(metric, n_trees=n_trees, distance_type=distance_type)
    click.echo("Finished.")
