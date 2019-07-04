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


@cli.command(name="update-metric")
@click.argument("metric")
@click.option("--batch-size", "-b", type=int, help="Override processing batch size.")
def update_metric(metric, batch_size=None):
    """Recomputes and updates a single metric in the
    similarity table for all recordings."""
    click.echo("Computing metric {}".format(metric))
    pass
    click.echo("Finished updating metric, exiting...")


@cli.command(name="delete-metric")
@click.argument("metric")
@click.option("--soft", "-s", is_flag=True, help="Don't delete data")
@click.option("--leave-stats", "-l", is_flag=True, help="Don't delete computed statistics")
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
@click.option("--n_trees", "-n", type=int, default=10, help="Number of trees for building")
@click.option("--distance_type", "-d", default='angular', help="Number of trees for building")
def add_index(metric, batch_size=None, n_trees=10, distance_type='angular'):
    """Creates an annoy index for the specified metric, adds all items to the index."""
    with db.engine.connect() as connection:
        click.echo("Initializing index...")
        index = AnnoyModel(connection, metric, n_trees=n_trees, distance_type=distance_type)

        batch_size = batch_size or PROCESS_BATCH_SIZE
        offset = 0
        count = 0

        result = connection.execute("""
            SELECT MAX(id)
              FROM similarity
        """)
        total = result.fetchone()[0]

        batch_query = text("""
            SELECT *
              FROM similarity
             ORDER BY id
             LIMIT :batch_size
            OFFSET :offset
        """)

        click.echo("Inserting items...")
        while True:
            # Get ids and vectors for specific metric in batches
            batch_result = connection.execute(batch_query, { "batch_size": batch_size, "offset": offset })
            if not batch_result.rowcount:
                click.echo("Finished adding items. Building index...")
                break

            for row in batch_result.fetchall():
                while not row["id"] == count:
                    # Rows are empty, add zero vector
                    placeholder = [0] * index.dimension
                    index.add_recording_with_vector(count, placeholder)
                    count += 1
                index.add_recording_with_vector(row["id"], row[index.metric_name])
                count += 1

            offset += batch_size
            click.echo("Items added: {}/{} ({:.3f}%)".format(offset, total, float(offset) / total * 100))

        index.build()
        click.echo("Saving index...")
        index.save()
        click.echo("Done!")


@cli.command(name='add-indices')
@click.option("--n-trees", "-n", default=10, type=int)
@click.option("--distance-type", "-d", default='angular')
def add_indices(n_trees=10, distance_type='angular'):
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
        add_index(metric, batch_size=None, n_trees=n_trees, distance_type=distance_type)
    click.echo("Finished.")


@cli.command(name='remove-index')
@click.argument("metric")
@click.option("--n_trees", "-n", type=int, default=10, help="Number of trees for building")
@click.option("--distance_type", "-d", default='angular', help="Number of trees for building")
def remove_index(metric, n_trees=10, distance_type='angular'):
    similarity.utils.remove_index(metric, n_trees, distance_type)
