"""Module for working with statistics on data stored in AcousticBrainz.

Values are stored in `statistics` table and are referenced by <name, timestamp>
pair.
"""
import db
import db.cache
import db.exceptions
import datetime
import time
import six

from sqlalchemy import text

STATS_CACHE_TIMEOUT = 60 * 10  # 10 minutes
LAST_MBIDS_CACHE_TIMEOUT = 60  # 1 minute (this query is cheap)

LOWLEVEL_LOSSY = "lowlevel-lossy"
LOWLEVEL_LOSSY_UNIQUE = "lowlevel-lossy-unique"
LOWLEVEL_LOSSLESS = "lowlevel-lossless"
LOWLEVEL_LOSSLESS_UNIQUE = "lowlevel-lossless-unique"
LOWLEVEL_TOTAL = "lowlevel-total"
LOWLEVEL_TOTAL_UNIQUE = "lowlevel-total-unique"


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
            result = connection.execute("""
                SELECT mbid,
                       data->'metadata'->'tags'->'artist'->>0,
                       data->'metadata'->'tags'->'title'->>0
                  FROM lowlevel
              ORDER BY id DESC
                 LIMIT 5
                OFFSET 10
            """)
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

def get_earliest_submission_date():
    """Get the earliest date that something was submitted to AB."""
    q = text("""SELECT submitted
                  FROM lowlevel
              ORDER BY submitted ASC
                 LIMIT 1""")
    with db.engine.connect() as connection:
        cur = connection.execute(q)
        row = cur.fetchone()
        if row:
            return row[0]

def get_most_recent_stats_date():
    q = text("""SELECT collected
                  FROM statistics
              ORDER BY collected DESC
                 LIMIT 1""")
    with db.engine.connect() as connection:
        cur = connection.execute(q)
        row = cur.fetchone()
        if row:
            return row[0]

def get_next_hour(date):
    """Round up a date to the nearest hour:00:00.
    Arguments:
      date: a datetime
    """
    delta = datetime.timedelta(hours=1)
    date = date + delta
    date = date.replace(minute=0, second=0, microsecond=0)
    return date

def compute_stats(to_date):
    # Compute stats up to the given date

    stats_date = get_most_recent_stats_date()
    if not stats_date:
        # If there have been no statistics, we start from the
        # earliest date in the lowlevel table
        stats_date = get_earliest_submission_date()
        if not stats_date:
            # If there are no lowlevel submissions, we stop
            return

    next_date = get_next_hour(stats_date)
    with db.engine.connect() as connection:
        while next_date < to_date:
            stats = _count_submissions_to_date(connection, next_date)
            write_stats(connection, next_date, stats)
            next_date = get_next_hour(next_date)

def write_stats(connection, date, stats):
    for name, value in six.iteritems(stats):
        """Records a value with a given name and current timestamp."""
        q = text("""
            INSERT INTO statistics (collected, name, value)
                 VALUES (:collected, :name, :value)""")
        connection.execute(q, {"collected": date, "name": name, "value": value})

def get_stats():
    """Get submission statistics based on low-level data.

    In addition, all stats are recorded in the database when this function is
    called if an hour has passed since last record.

    Returns:
        Dictionary with values for each metric:
        - lowlevel-lossy: total number of lossy submissions
        - lowlevel-lossless: total number of lossless submissions
        - lowlevel-lossy-unique: number of unique lossy submissions
        - lowlevel-lossless-unique: number of unique lossless submissions
    """

    # Names are also used as cache keys with prefix defined below.
    stats_names = [
        LOWLEVEL_LOSSY,
        LOWLEVEL_LOSSLESS,
        LOWLEVEL_LOSSY_UNIQUE,
        LOWLEVEL_LOSSLESS_UNIQUE,
        LOWLEVEL_TOTAL,
        LOWLEVEL_TOTAL_UNIQUE,
    ]
    cache_key_prefix = "ac-num-"
    # TODO: Port this to new implementation (don't use protected parts):
    stats = db.cache._mc.get_multi(stats_names, key_prefix=cache_key_prefix)

    # Last collected value is used as an indication if we need to recalculate
    # all the values. It's stored in cache for MIN_RECORD_INTERVAL seconds (see
    # definition above).
    last_collected_cache_key = "last-collected"
    last_collected = db.cache.get(last_collected_cache_key)

    # All stats need to be recalculated together!
    # Checking if one of values is missing or if we hit the stats recording time.
    if sorted(stats_names) != sorted(stats.keys()) or last_collected is None:

        with db.engine.connect() as connection:
            stats = _get_latest_stats(connection)
            last_collected = _current_db_time(connection)

        # TODO: Port this to new implementation:
        db.cache._mc.set_multi(stats, key_prefix=cache_key_prefix, time=STATS_CACHE_TIMEOUT)
        db.cache.set(last_collected_cache_key, last_collected, time=STATS_CACHE_TIMEOUT)

    return stats, last_collected


def get_statistics_data():
    stats_key_map = {
        LOWLEVEL_LOSSY: "Lossy (all)",
        LOWLEVEL_LOSSY_UNIQUE: "Lossy (unique)",
        LOWLEVEL_LOSSLESS: "Lossless (all)",
        LOWLEVEL_LOSSLESS_UNIQUE: "Lossless (unique)",
        LOWLEVEL_TOTAL: "Total (all)",
        LOWLEVEL_TOTAL_UNIQUE: "Total (unique)",
    }

    stats = []

    with db.engine.connect() as connection:
        stats_result = connection.execute("""
            SELECT name,
                   array_agg(collected ORDER BY collected ASC) AS times,
                   array_agg(value ORDER BY collected ASC) AS values
              FROM statistics
          GROUP BY name
        """)
        for name, times, values in stats_result:
            # <time, value> pairs
            pairs = zip([_make_timestamp(t) for t in times], values)

            stats.append({
                "name": stats_key_map.get(name, name),
                "data": [[p[0], p[1]] for p in pairs]
            })

    return stats


def _count_submissions_to_date(connection, to_date):
    """Count number of low-level submissions in the database."""
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
    dt = dt.replace(microsecond=0)
    return time.mktime(dt.utctimetuple())*1000
