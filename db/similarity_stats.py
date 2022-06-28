import db
import similarity.utils

from sqlalchemy import text
import numpy as np

NORMALIZATION_SAMPLE_SIZE = 10000

"""
Normalized metrics for determining similarity require
vectors to be transformed based on the mean and standard
deviation of their associated lowlevel feature (currently
MFCC, GFCC unweighted and weighted).

Similarity stats must be computed before metrics can be
added and indices can be built.

Stats can be computed using the `similarity/manage.py`
init command.

We use a random sample, defaulting at 10000 items, to
approximate these statistics for the entire lowlevel
table before inserting them in similarity.similarity_stats.
"""


def compute_stats(sample_size, force=False):
    """Compute mean and stddev for each of the features
    required by similarity metrics. These stats are then
    inserted into the similarity.similarity_stats table.

    *NOTE*: Currently, metrics that require stats to be
    computed must be hardcoded alongside the path to their
    associated features. For now, stats are only needed for
    unweighted/weighted MFCC and GFCC metrics.

    Args:
        sample_size: The number of lowlevel entries that
        will be used to approximate mean and stddev.
    """
    if force:
        db.similarity_stats.delete_similarity_stats()

    # Build features and metrics lists
    metrics = similarity.utils.init_metrics()
    metric_names = []
    metric_paths = {}
    for metric in metrics:
        if hasattr(metric, 'means') and hasattr(metric, 'stddevs'):
            # Stats should be computed if attributes are present
            metric_paths[metric.name] = metric.path
            metric_names.append(metric.name)

    entries = get_random_sample_lowlevel(sample_size, metric_paths)
    features = {}
    for name in metric_names:
        data = [row[name] for row in entries]
        mean = np.mean(data, axis=0).tolist()
        stdev = np.std(data, axis=0).tolist()
        features[name] = {"mean": mean, "stdev": stdev}
    insert_similarity_stats(features)


def get_random_sample_lowlevel(sample_size, features):
    """Collects a random sample for select lowlevel features.

    *NOTE*: Sample size should be >= 1% of the lowlevel_json entries.

    Args:
        sample_size: Integer, number of sample lowlevel entries that
        should be collected, at random. Must be >= 1% of the entries
        in lowlevel_json.

        features: A dictionary of postgres json query paths that should be collected
        in each row of the sample. The key of the dictionary is what the column alias
        should be, e.g.
        {
            "mean": "data->'lowlevel'->'gfcc'->'mean'"
        }

    Returns:
        A list of tuples (mfcc_vector, gfcc_vector) for each random
        lowlevel entry.
    """
    with db.engine.connect() as connection:
        count_query = text("""
            SELECT count(*) AS count
              FROM lowlevel
        """)
        result = connection.execute(count_query)
        count = result.fetchone()["count"]
        if count < 1:
            raise db.exceptions.NoDataFoundException('Statistics cannot be calculated without lowlevel submissions.')

        sample_query = text("""
            SELECT %(features)s
              FROM lowlevel_json
TABLESAMPLE SYSTEM ((:sample_size * 100) / :count)
        """ % {"features": ', '.join(["{path} as {alias}".format(path=path, alias=alias) for alias, path in features.items()])})

        result = connection.execute(sample_query, {"sample_size": sample_size,
                                                   "count": float(count)})
        if not result.rowcount:
            raise db.exceptions.NoDataFoundException('Statistics cannot be calculated without lowlevel submissions.')
        return [dict(row) for row in result.fetchall()]


def insert_similarity_stats(features):
    """Inserts computed mean and stddev for MFCC and GFCC
    into similarity.similarity_stats table.

    Args:
        features: a dictionary of featurename: data
          where data is a dictionary with keys "mean" and "stdev"
    """
    # TODO: Make this dynamic rather than hardcoded for only mfccs/gfcss.
    with db.engine.connect() as connection:
        query = text("""
        INSERT INTO similarity.similarity_stats (metric, means, stddevs)
             VALUES ('gfccsw', :gfccsw_means, :gfccsw_stddevs),
                    ('gfccs', :gfccs_means, :gfccs_stddevs),
                    ('mfccs', :mfccs_means, :mfccs_stddevs),
                    ('mfccsw', :mfccsw_means, :mfccsw_stddevs)
        ON CONFLICT
         DO NOTHING
        """)
        connection.execute(query, {"gfccsw_means": features["gfccsw"]["mean"],
                                   "gfccsw_stddevs": features["gfccsw"]["stdev"],
                                   "gfccs_means": features["gfccs"]["mean"],
                                   "gfccs_stddevs": features["gfccs"]["stdev"],
                                   "mfccs_means": features["mfccs"]["mean"],
                                   "mfccs_stddevs": features["mfccs"]["stdev"],
                                   "mfccsw_means": features["mfccsw"]["mean"],
                                   "mfccsw_stddevs": features["mfccsw"]["stdev"]})


def delete_similarity_stats():
    with db.engine.connect() as connection:
        query = text("""
            DELETE FROM similarity.similarity_stats
        """)
        connection.execute(query)


def assign_stats(metric):
    """Collect computed stats from similarity.similarity_stats
    if the metric requires them.

    Args:
        metric: an instance of a metric class, specifically
        one that requires normalization from similarity/metrics.py.
    """
    if hasattr(metric, "means") and hasattr(metric, "stddevs"):
        with db.engine.connect() as connection:
            query = text("""
                SELECT means, stddevs
                  FROM similarity.similarity_stats
                 WHERE metric = :metric
            """)
            result = connection.execute(query, {"metric": metric.name})
            if not result.rowcount:
                raise db.exceptions.NoDataFoundException("Stats have not been calculated for metric {}".format(metric.name))
            row = result.fetchone()
            metric.means = row["means"]
            metric.stddevs = row["stddevs"]
