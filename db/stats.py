"""Module for working with statistics on data stored in AcousticBrainz.

Values are stored in `statistics` table and are referenced by <name, timestamp>
pair.
"""
import db
import db.cache
import db.exceptions
import datetime
import pytz
import calendar
import six

from sqlalchemy import text

STATS_CACHE_TIMEOUT = 60 * 10  # 10 minutes
LAST_MBIDS_CACHE_TIMEOUT = 60  # 1 minute (this query is cheap)

STATS_MEMCACHE_KEY = "recent-stats"
STATS_MEMCACHE_LAST_UPDATE_KEY = "recent-stats-last-updated"
STATS_MEMCACHE_NAMESPACE = "statistics"

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
    last_submissions = db.cache.get(cache_key)
    if not last_submissions:
        with db.engine.connect() as connection:
            # We are getting results with of offset of 10 rows because we'd
            # prefer to show recordings for which we already calculated
            # high-level data. This might not be the best way to do that.
            result = connection.execute("""SELECT ll.mbid,
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
                    "mbid": r[0],
                    "artist": r[1],
                    "title": r[2],
                } for r in last_submissions if r[1] and r[2]
            ]
        db.cache.set(cache_key, last_submissions, time=LAST_MBIDS_CACHE_TIMEOUT)

    return last_submissions


def compute_stats(to_date):
    """Compute hourly stats to a given date and write them to
    the database.

    Take the date of most recent statistics, or if no statistics
    are added, the earliest date of a submission, and compute and write
    for every hour from that date to `to_date` the number of items
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

        next_date = _get_next_hour(stats_date)

        while next_date < to_date:
            stats = _count_submissions_to_date(connection, next_date)
            _write_stats(connection, next_date, stats)
            next_date = _get_next_hour(next_date)


def _write_stats(connection, date, stats):
    """Records a value with a given name and current timestamp."""
    for name, value in six.iteritems(stats):
        q = text("""
            INSERT INTO statistics (collected, name, value)
                 VALUES (:collected, :name, :value)""")
        connection.execute(q, {"collected": date, "name": name, "value": value})


def add_stats_to_cache():
    """Compute the most recent statistics and add them to memcache"""
    now = datetime.datetime.now(pytz.utc)
    with db.engine.connect() as connection:
        stats = _count_submissions_to_date(connection, now)
        db.cache.set(STATS_MEMCACHE_KEY, stats,
                     time=STATS_CACHE_TIMEOUT, namespace=STATS_MEMCACHE_NAMESPACE)
        db.cache.set(STATS_MEMCACHE_LAST_UPDATE_KEY, now,
                     time=STATS_CACHE_TIMEOUT, namespace=STATS_MEMCACHE_NAMESPACE)


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
    """Get submission statistics from memcache"""
    stats = db.cache.get(STATS_MEMCACHE_KEY, namespace=STATS_MEMCACHE_NAMESPACE)
    last_collected = db.cache.get(STATS_MEMCACHE_LAST_UPDATE_KEY,
                                  namespace=STATS_MEMCACHE_NAMESPACE)

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
            counts[k].append([ts, stats[k]])

    stats = [{"name": stats_key_map.get(key, key), "data": data} for key, data in counts.items()]

    return stats


def load_statistics_data(limit=None):
    # Postgres doesn't let you create a json dictionary using values
    # from one column as keys and another column as values. Instead we
    # create an array of {"name": name, "value": value} objects and change
    # it in python
    args = {}
    # TODO: use sqlalchemy select().limit()?
    qtext = """
            SELECT collected
                 , json_agg(row_to_json(
                    (SELECT r FROM (SELECT name, value) r) )) AS stats
              FROM statistics
          GROUP BY collected
          ORDER BY collected DESC
          """
    if limit:
        args["limit"] = int(limit)
        qtext += " LIMIT :limit"
    query = text(qtext)
    with db.engine.connect() as connection:
        stats_result = connection.execute(query, args)
        ret = []
        for line in stats_result:
            row = {"collected": line["collected"], "stats": {}}
            for stat in line["stats"]:
                row["stats"][stat["name"]] = stat["value"]
            ret.append(row)

    # We order by DESC in order to use the `limit` parameter, but
    # we actually need the stats in increasing order.
    return list(reversed(ret))


def get_statistics_history():
    return format_statistics_for_highcharts(load_statistics_data())


def _count_submissions_to_date(connection, to_date):
    """Count number of low-level submissions in the database
    before a given date."""
    # Both total submissions and unique (based on MBIDs)
    query = text("""
        SELECT 'all' as type, lossless, count(*)
          FROM lowlevel
         WHERE submitted < :submitted
      GROUP BY lossless
         UNION
        SELECT 'unique' as type, lossless, count(*)
          FROM (
                SELECT DISTINCT ON (mbid) mbid, lossless
                  FROM lowlevel
                 WHERE submitted < :submitted
              ORDER BY mbid, lossless DESC
               ) q
      GROUP BY lossless
    """)
    result = connection.execute(query, {"submitted": to_date})
    counts = {
        LOWLEVEL_LOSSY: 0,
        LOWLEVEL_LOSSY_UNIQUE: 0,
        LOWLEVEL_LOSSLESS: 0,
        LOWLEVEL_LOSSLESS_UNIQUE: 0,
        LOWLEVEL_TOTAL: 0,
        LOWLEVEL_TOTAL_UNIQUE: 0,
    }
    for count_type, is_lossless, count in result.fetchall():
        if count_type == "all":
            if is_lossless:
                counts[LOWLEVEL_LOSSLESS] = count
            else:
                counts[LOWLEVEL_LOSSY] = count
        else:  # unique
            if is_lossless:
                counts[LOWLEVEL_LOSSLESS_UNIQUE] = count
            else:
                counts[LOWLEVEL_LOSSY_UNIQUE] = count
    counts[LOWLEVEL_TOTAL] = counts[LOWLEVEL_LOSSY] + counts[LOWLEVEL_LOSSLESS]
    counts[LOWLEVEL_TOTAL_UNIQUE] = counts[LOWLEVEL_LOSSY_UNIQUE] + counts[LOWLEVEL_LOSSLESS_UNIQUE]
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


def _get_next_hour(date):
    """Round up a date to the nearest hour:00:00.
    Arguments:
      date: a datetime
    """
    delta = datetime.timedelta(hours=1)
    date = date + delta
    date = date.replace(minute=0, second=0, microsecond=0)
    return date
