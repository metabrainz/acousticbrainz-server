from __future__ import print_function
from flask.cli import FlaskGroup
import click

import webserver
import metrics
from operations import HybridMetric
from index_model import AnnoyModel
import db

from sqlalchemy import text

PROCESS_BATCH_SIZE = 10000

cli = FlaskGroup(add_default_commands=False, create_app=webserver.create_app_flaskgroup)


@cli.command()
def init_similarity():
    click.echo('Copying data')
    with db.engine.begin() as connection:
        query = text("""
        INSERT INTO similarity(id)
             SELECT id
               FROM lowlevel
        """)
        connection.execute(query)


def _get_recordings_without_similarity(connection, name, batch_size):
    query = text("""
        SELECT id
          FROM similarity
         WHERE %(metric)s IS NULL
         LIMIT %(limit)s
    """ % {'metric': name, 'limit': batch_size})
    result = connection.execute(query)
    rows = result.fetchall()
    if not rows:
        return []
    ids = zip(*rows)[0]
    return ids


def _update_similarity(connection, name, row_id, vector, isnan=False):
    value = '[' + ', '.join(["'NaN'::double precision"] * len(vector)) + ']' if isnan else str(list(vector))
    query = text("""
        UPDATE similarity
           SET %(metric)s = %(value)s
         WHERE id = %(id)s
    """ % {'metric': name, 'value': 'ARRAY' + value, 'id': row_id})
    connection.execute(query)


@cli.command(name="add-metric")
@click.argument("name")
@click.option("--force", "-f", is_flag=True, help="Recompute existing metrics.")
@click.option("--to-process", "-t", type=int, help="Only process limited number of rows")
@click.option("--batch-size", "-b", type=int, help="Override processing batch size")
def add_metric(name, force=False, to_process=None, batch_size=None):
    try:
        metric_cls = metrics.BASE_METRICS[name]
    except KeyError:
        click.echo("No such metric is implemented: {}".format(name))
        return

    with db.engine.connect() as connection:
        metric = metric_cls(connection)
        metric.create(clear=force)

        query = text("""
            SELECT count(*), count(%s)
              FROM similarity
        """ % name)
        result = connection.execute(query)
        total, past = result.fetchone()
        current = past
        to_process = to_process or total - past

        try:
            metric.calculate_stats()
        except AttributeError:
            pass

        batch_size = batch_size or PROCESS_BATCH_SIZE

        click.echo('Started processing, {} / {} ({:.3f}%) already processed'.format(
            current, total, float(current) / total * 100))
        ids = _get_recordings_without_similarity(connection, name, batch_size)

        while len(ids) > 0 and (current - past < to_process):
            with connection.begin():
                for row_id, data in metric.get_data_batch(ids):
                    try:
                        vector = metric.transform(data)
                        isnan = False
                    except ValueError:
                        vector = [None] * metric.length()
                        isnan = True
                    _update_similarity(connection, name, row_id, vector, isnan=isnan)

            current += len(ids)

            click.echo('Processing {} / {} ({:.3f}%)'.format(current, total, float(current) / total * 100))
            ids = _get_recordings_without_similarity(connection, name, batch_size)

    return current


@cli.command(name="delete-metric")
@click.argument("name")
@click.option("--soft", "-s", is_flag=True, help="Don't delete data")
@click.option("--leave-stats", "-l", is_flag=True, help="Don't delete computed statistics")
def delete_metric(name, soft=False, leave_stats=False):
    try:
        metric_cls = metrics.BASE_METRICS[name]
    except KeyError:
        click.echo('No such metric is implemented: {}'.format(name))
        return

    with db.engine.begin() as connection:
        metric = metric_cls(connection)
        metric.delete(soft=soft)

        if not leave_stats:
            try:
                metric.delete_stats()
            except AttributeError:
                pass


@cli.command(name="add-hybrid")
@click.argument("name")
@click.argument("category")
@click.option("--description", "-d", type=str, help="Description of metric")
def add_hybrid(name, category, description=None):
    description = description or name
    with db.engine.begin() as connection:
        metric = HybridMetric(connection, name, category, description)
        metric.create()


@cli.command(name="delete-hybrid")
@click.argument("name")
def delete_hybrid(name):
    with db.engine.begin() as connection:
        metric = HybridMetric(connection, name)
        metric.delete()


# @cli.command(name='add-index')
# @click.argument("metric")
# @click.option("--batch_size", "-b", type=int, help="Size of batches")
# @click.option("--n_trees", "-n", type=int, help="Number of trees for building")
def add_index(metric, batch_size=None, n_trees=10, distance_type='angular'):
    """Creates an annoy index for the specified metric, adds all items to the index."""
    with db.engine.connect() as connection:
        click.echo("Initializing index...")
        index = AnnoyModel(connection, metric, n_trees, distance_type)

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
@click.option("--n-trees", "-n", type=int)
@click.option("--distance-type", "-d")
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
