"""Module for working with statistics on data stored in AcousticBrainz.

Values are stored in `statistics` table and are referenced by <name, timestamp>
pair.
"""
from brainzutils import cache
from sqlalchemy.dialects.postgresql import JSONB

import db
import db.exceptions
import datetime
import pytz
import calendar
import six
import json

from sqlalchemy import text, bindparam

STATS_CACHE_TIMEOUT = 60 * 60  # 1 hour
LAST_MBIDS_CACHE_TIMEOUT = 60  # 1 minute (this query is cheap)

STATS_CACHE_KEY = "recent-stats"
STATS_CACHE_LAST_UPDATE_KEY = "recent-stats-last-updated"
STATS_CACHE_NAMESPACE = "statistics"

LOWLEVEL_LOSSY = "lowlevel-lossy"
LOWLEVEL_LOSSY_UNIQUE = "lowlevel-lossy-unique"
LOWLEVEL_LOSSLESS = "lowlevel-lossless"
LOWLEVEL_LOSSLESS_UNIQUE = "lowlevel-lossless-unique"
LOWLEVEL_TOTAL = "lowlevel-total"
LOWLEVEL_TOTAL_UNIQUE = "lowlevel-total-unique"

stats_key_map = {
    LOWLEVEL_LOSSY: "Lossy (all)",
    LOWLEVEL_LOSSY_UNIQUE: "Lossy (unique)",
    LOWLEVEL_LOSSLESS: "Lossless (all)",
    LOWLEVEL_LOSSLESS_UNIQUE: "Lossless (unique)",
    LOWLEVEL_TOTAL: "Total (all)",
    LOWLEVEL_TOTAL_UNIQUE: "Total (unique)",
}


def get_last_submitted_recordings():
    """Get list of last submitted recordings.

    Returns:
        List of dictionaries with basic info about last submitted recordings:
        mbid (MusicBrainz ID), artist (name), and title.
    """
    cache_key = "last-submitted-recordings"
    last_submissions = cache.get(cache_key)
    if not last_submissions:
        with db.engine.connect() as connection:
            # We are getting results with of offset of 10 rows because we'd
            # prefer to show recordings for which we already calculated
            # high-level data. This might not be the best way to do that.
            result = connection.execute("""SELECT ll.gid,
                                     llj.data->'metadata'->'tags'->'artist'->>0,
                                     llj.data->'metadata'->'tags'->'title'->>0
                                FROM lowlevel ll
                                JOIN lowlevel_json llj
                                  ON ll.id = llj.id
                            ORDER BY ll.id DESC
                               LIMIT 5
                              OFFSET 10""")
            last_submissions = result.fetchall()
            last_submissions = [
                {
                    "mbid": str(r[0]),
                    "artist": r[1],
                    "title": r[2],
                } for r in last_submissions if r[1] and r[2]
            ]
        cache.set(cache_key, last_submissions, time=LAST_MBIDS_CACHE_TIMEOUT)

    return last_submissions


def compute_stats(to_date):
    """Compute daily stats to a given date and write them to
    the database.

    Take the date of most recent statistics, or if no statistics
    are added, the earliest date of a submission, and compute and write
    for every day from that date to `to_date` the number of items
    in the database.

    Args:
        to_date: the date to compute statistics up to
    """

    with db.engine.connect() as connection:
        stats_date = _get_most_recent_stats_date(connection)
        if not stats_date:
            # If there have been no statistics, we start from the
            # earliest date in the lowlevel table
            stats_date = _get_earliest_submission_date(connection)
            if not stats_date:
                # If there are no lowlevel submissions, we stop
                return

        next_date = _get_next_day(stats_date)

        while next_date < to_date:
            stats = _count_submissions_to_date(connection, next_date)
            _write_stats(connection, next_date, stats)
            next_date = _get_next_day(next_date)


def _write_stats(connection, date, stats):
    """Records a value with a given name and current timestamp."""

    if len(stats) != len(stats_key_map):
        raise ValueError("provided stats map is of unexpected size")
    for k, v in stats.items():
        try:
            int(v)
        except ValueError:
            raise ValueError("value %s in map isn't an integer" % v)
    query = text("""
        INSERT INTO statistics (collected, stats)
             VALUES (:collected, :stats)""").bindparams(bindparam('stats', type_=JSONB))
    connection.execute(query, {"collected": date, "stats": stats})


def add_stats_to_cache():
    """Compute the most recent statistics and add them to cache"""
    now = datetime.datetime.now(pytz.utc)
    with db.engine.connect() as connection:
        stats = _count_submissions_to_date(connection, now)
        cache.set(STATS_CACHE_KEY, stats,
                  time=STATS_CACHE_TIMEOUT, namespace=STATS_CACHE_NAMESPACE)
        cache.set(STATS_CACHE_LAST_UPDATE_KEY, now,
                  time=STATS_CACHE_TIMEOUT, namespace=STATS_CACHE_NAMESPACE)


def get_stats_summary():
    """Load a summary of statistics to show on the homepage.

    If no statistics exist in the cache, use the most recently
    computed statistics from the database
    """
    last_collected, stats = _get_stats_from_cache()
    if not stats:
        recent_database = load_statistics_data(1)
        if recent_database:
            stats = recent_database[0]["stats"]
            last_collected = recent_database[0]["collected"]
        else:
            stats = {k: 0 for k in stats_key_map.keys()}
    return stats, last_collected


def _get_stats_from_cache():
    """Get submission statistics from cache"""
    stats = cache.get(STATS_CACHE_KEY, namespace=STATS_CACHE_NAMESPACE)
    last_collected = cache.get(STATS_CACHE_LAST_UPDATE_KEY,
                               namespace=STATS_CACHE_NAMESPACE)

    # TODO: See BU-28, a datetime from the cache loses its timezone. In this case we
    #       know that it's at utc, so force it
    if last_collected:
        last_collected = pytz.utc.localize(last_collected)
    return last_collected, stats


def format_statistics_for_highcharts(data):
    """Format statistics data to load with highcharts

    Args:
        data: data from load_statistics_data
    """

    counts = {}
    for k in stats_key_map.keys():
        counts[k] = []

    for row in data:
        collected = row["collected"]
        stats = row["stats"]

        ts = _make_timestamp(collected)
        for k, v in counts.items():
            counts[k].append([ts, stats.get(k, 0)])

    stats = [{"name": stats_key_map.get(key, key), "data": data} for key, data in counts.items()]

    return stats


def load_statistics_data(limit=None):
    args = {}
    qtext = """SELECT collected, stats
                 FROM statistics
             ORDER BY collected DESC
          """
    if limit:
        args["limit"] = int(limit)
        qtext += " LIMIT :limit"
    query = text(qtext)
    with db.engine.connect() as connection:
        stats_result = connection.execute(query, args)
        # We order by DESC in order to use the `limit` parameter, but
        # we actually need the stats in increasing order.
        return list(reversed([dict(r) for r in stats_result]))


def get_statistics_history():
    stats = load_statistics_data()
    cached_stats_date, cached_stats = _get_stats_from_cache()
    # If cached stats exist and it's newer than the most recent database stats,
    # add it to the end. Don't add cached stats if there are no database stats
    if cached_stats_date and stats:
        last_stats_collected = stats[-1]["collected"]
        if cached_stats_date > last_stats_collected:
            stats.append({"collected": cached_stats_date, "stats": cached_stats})
    return format_statistics_for_highcharts(stats)


def _count_submissions_to_date(connection, to_date):
    """Count number of low-level submissions in the database
    before a given date."""

    counts = {
        LOWLEVEL_LOSSY: 0,
        LOWLEVEL_LOSSY_UNIQUE: 0,
        LOWLEVEL_LOSSLESS: 0,
        LOWLEVEL_LOSSLESS_UNIQUE: 0,
        LOWLEVEL_TOTAL: 0,
        LOWLEVEL_TOTAL_UNIQUE: 0,
    }

    # All submissions, split by lossless/lossy
    query = text("""
        SELECT lossless
             , count(*)
          FROM lowlevel
         WHERE submitted < :submitted
      GROUP BY lossless
      """)
    result = connection.execute(query, {"submitted": to_date})
    for is_lossless, count in result.fetchall():
        if is_lossless:
            counts[LOWLEVEL_LOSSLESS] = count
        else:
            counts[LOWLEVEL_LOSSY] = count

    # Unique submissions, split by lossless, lossy
    query = text("""
        SELECT lossless
             , count(distinct(gid))
          FROM lowlevel
         WHERE submitted < :submitted
      GROUP BY lossless
    """)
    result = connection.execute(query, {"submitted": to_date})
    for is_lossless, count in result.fetchall():
        if is_lossless:
            counts[LOWLEVEL_LOSSLESS_UNIQUE] = count
        else:
            counts[LOWLEVEL_LOSSY_UNIQUE] = count

    # total number of unique submissions
    query = text("""
        SELECT count(distinct(gid))
          FROM lowlevel
         WHERE submitted < :submitted
    """)
    result = connection.execute(query, {"submitted": to_date})
    row = result.fetchone()
    counts[LOWLEVEL_TOTAL_UNIQUE] = row[0]

    # total of all submissions can be computed by summing lossless and lossy
    counts[LOWLEVEL_TOTAL] = counts[LOWLEVEL_LOSSY] + counts[LOWLEVEL_LOSSLESS]
    return counts


def _make_timestamp(dt):
    """ Return the number of miliseconds since the epoch, in UTC """
    dt = dt.replace(microsecond=0)
    return calendar.timegm(dt.utctimetuple())*1000


def _get_earliest_submission_date(connection):
    """Get the earliest date that something was submitted to AB."""
    q = text("""SELECT submitted
                  FROM lowlevel
              ORDER BY submitted ASC
                 LIMIT 1""")
    cur = connection.execute(q)
    row = cur.fetchone()
    if row:
        return row[0]


def _get_most_recent_stats_date(connection):
    q = text("""SELECT collected
                  FROM statistics
              ORDER BY collected DESC
                 LIMIT 1""")
    cur = connection.execute(q)
    row = cur.fetchone()
    if row:
        return row[0]


def _get_next_day(date):
    """Round up a date to the nearest day:00:00:00

    Arguments:
        date: a datetime
    """
    delta = datetime.timedelta(days=1)
    date = date + delta
    date = date.replace(hour=0, minute=0, second=0, microsecond=0)
    return date
