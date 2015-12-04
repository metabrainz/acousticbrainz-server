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

STATS_CACHE_TIMEOUT = 60 * 10  # 10 minutes
LAST_MBIDS_CACHE_TIMEOUT = 60  # 1 minute (this query is cheap)

LOWLEVEL_LOSSY = "lowlevel-lossy"
LOWLEVEL_LOSSY_UNIQUE = "lowlevel-lossy-unique"
LOWLEVEL_LOSSLESS = "lowlevel-lossless"
LOWLEVEL_LOSSLESS_UNIQUE = "lowlevel-lossless-unique"


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

        stats = dict([(name, 0) for name in stats_names])

        with db.engine.connect() as connection:
            # FIXME(roman): Ideally all these stats should be calculated in one
            # query which would also get current time, for better accuracy.
            stats[LOWLEVEL_LOSSLESS], stats[LOWLEVEL_LOSSY] = \
                _count_all_submissions(connection)
            stats[LOWLEVEL_LOSSLESS_UNIQUE], stats[LOWLEVEL_LOSSY_UNIQUE] = \
                _count_unique_submissions(connection)

            # Recordings stats in the database, if necessary
            if _is_update_time(connection):
                for name, value in six.iteritems(stats):
                    _record_value(connection, name, value)

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
        LOWLEVEL_LOSSLESS_UNIQUE: "Lossless (unique)"
    }

    total_all = {"name": "Total (all)", "data": {}}
    total_unique = {"name": "Total (unique)", "data": {}}

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

            if name in [LOWLEVEL_LOSSY, LOWLEVEL_LOSSLESS]:
                total_dict_ref = total_all
            elif name in [LOWLEVEL_LOSSY_UNIQUE, LOWLEVEL_LOSSLESS_UNIQUE]:
                total_dict_ref = total_unique
            else:
                raise db.exceptions.DatabaseException("Unexpected name in stats.")
            for timestamp, value in pairs:
                if timestamp in total_dict_ref["data"]:
                    total_dict_ref["data"][timestamp] = total_dict_ref["data"][timestamp] + value
                else:
                    total_dict_ref["data"][timestamp] = value

    total_all['data'] = [[k, total_all['data'][k]] for k in sorted(total_all['data'].keys())]
    total_unique['data'] = [[k, total_unique['data'][k]] for k in sorted(total_unique['data'].keys())]

    stats.extend([total_all, total_unique])

    return stats


def _is_update_time(connection):
    """Checks if it's time to record statistics in the database.

    Minimum time between records is one hour.

    Args:
        connection: Database connection.

    Returns:
        True if it's time to write new stats, False otherwise.
    """
    last_check_result = connection.execute("""
        SELECT now() as now, collected
          FROM statistics
      ORDER BY collected DESC
         LIMIT 1
    """)
    if last_check_result.rowcount > 0:
        now, last_collected = last_check_result.fetchone()
    return last_check_result.rowcount == 0 or now - last_collected > datetime.timedelta(minutes=59)


def _record_value(connection, name, value):
    """Records a value with a given name and current timestamp."""
    connection.execute("""
        INSERT INTO statistics (collected, name, value)
             VALUES (now(), %s, %s)
          RETURNING collected
    """, (name, value))


def _count_all_submissions(connection):
    """Count total number of low-level submissions in the database.

    Args:
        connection: Database connection.

    Returns:
        Tuple with two values: first is number of lossless submissions, second
        is number of lossy submissions.
    """
    result = connection.execute("""
        SELECT lossless, count(*)
          FROM lowlevel
      GROUP BY lossless
    """)
    # Should return two rows (one with lossy count, another with lossless)
    lossless_count = 0
    lossy_count = 0
    for is_lossless, count in result.fetchall():
        if is_lossless:
            lossless_count = count
        else:
            lossy_count = count
    return lossless_count, lossy_count


def _count_unique_submissions(connection):
    """Count number of unique low-level submissions in the database.

    Unique means that they correspond to different recordings.

    Args:
        connection: Database connection.

    Returns:
        Tuple with two values: first is number of unique lossless submissions,
        second is number of unique lossy submissions.
    """
    result = connection.execute("""
        SELECT lossless, count(*)
          FROM (
                  SELECT DISTINCT ON (mbid) mbid, lossless
                    FROM lowlevel
                ORDER BY mbid, lossless DESC
               ) q
      GROUP BY lossless
    """)
    # Should return two rows (one with lossy count, another with lossless)
    lossless_count = 0
    lossy_count = 0
    for is_lossless, count in result.fetchall():
        if is_lossless:
            lossless_count = count
        else:
            lossy_count = count
    return lossless_count, lossy_count


def _current_db_time(connection):
    return connection.execute("SELECT now()").fetchone()[0]


def _make_timestamp(dt):
    return (time.mktime(dt.utctimetuple()) * 1000) + (dt.microsecond / 1000)
