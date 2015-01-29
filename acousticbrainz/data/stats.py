import psycopg2
from flask import current_app
import datetime
import memcache
import time


STATS_CACHE_TIMEOUT = 60 * 10  # ten minutes
LAST_MBIDS_CACHE_TIMEOUT = 60  # 1 minute (this query is cheap)


def get_last_submitted_tracks():
    mc = memcache.Client(['127.0.0.1:11211'], debug=0)
    last_submitted_data = mc.get('last-submitted-data')
    if not last_submitted_data:
        conn = psycopg2.connect(current_app.config['PG_CONNECT'])
        cur = conn.cursor()
        cur.execute("""SELECT mbid,
                              data->'metadata'->'tags'->'artist'->>0,
                              data->'metadata'->'tags'->'title'->>0
                         FROM lowlevel
                     ORDER BY id DESC
                        LIMIT 5
                       OFFSET 10""")
        last_submitted_data = cur.fetchall()
        last_submitted_data = [
            (r[0], r[1].decode("UTF-8"), r[2].decode("UTF-8"))
            for r in last_submitted_data
        ]
        mc.set('last-submitted-data', last_submitted_data, time=LAST_MBIDS_CACHE_TIMEOUT)

    return last_submitted_data


def get_stats():
    mc = memcache.Client(['127.0.0.1:11211'], debug=0)
    stats_keys = ["lowlevel-lossy", "lowlevel-lossy-unique", "lowlevel-lossless", "lowlevel-lossless-unique"]
    stats = mc.get_multi(stats_keys, key_prefix="ac-num-")
    last_collected = mc.get('last-collected')

    # Recalculate everything together, always.
    if sorted(stats_keys) != sorted(stats.keys()) or last_collected is None:
        stats_parameters = dict([(a, 0) for a in stats_keys])

        conn = psycopg2.connect(current_app.config['PG_CONNECT'])
        cur = conn.cursor()
        cur.execute("SELECT now() as now, collected FROM statistics ORDER BY collected DESC LIMIT 1")
        update_db = False
        if cur.rowcount > 0:
            (now, last_collected) = cur.fetchone()
        if cur.rowcount == 0 or now - last_collected > datetime.timedelta(minutes=59):
            update_db = True

        cur.execute("SELECT lossless, count(*) FROM lowlevel GROUP BY lossless")
        for row in cur.fetchall():
            if row[0]: stats_parameters['lowlevel-lossless'] = row[1]
            if not row[0]: stats_parameters['lowlevel-lossy'] = row[1]

        cur.execute("SELECT lossless, count(*) FROM (SELECT DISTINCT ON (mbid) mbid, lossless FROM lowlevel ORDER BY mbid, lossless DESC) q GROUP BY lossless;")
        for row in cur.fetchall():
            if row[0]: stats_parameters['lowlevel-lossless-unique'] = row[1]
            if not row[0]: stats_parameters['lowlevel-lossy-unique'] = row[1]

        if update_db:
            for key, value in stats_parameters.iteritems():
                cur.execute("INSERT INTO statistics (collected, name, value) VALUES (now(), %s, %s) RETURNING collected", (key, value))
            conn.commit()

        cur.execute("SELECT now()")
        last_collected = cur.fetchone()[0]
        value = stats_parameters

        mc.set_multi(stats_parameters, key_prefix="ac-num-", time=STATS_CACHE_TIMEOUT)
        mc.set('last-collected', last_collected, time=STATS_CACHE_TIMEOUT)
    else:
        value = stats

    return value, last_collected


def get_statistics_data():
    conn = psycopg2.connect(current_app.config['PG_CONNECT'])
    cur = conn.cursor()
    cur.execute("SELECT name, array_agg(collected ORDER BY collected ASC) AS times, array_agg(value ORDER BY collected ASC) AS values FROM statistics GROUP BY name");
    stats_key_map = {
        "lowlevel-lossy": "Lossy (all)",
        "lowlevel-lossy-unique": "Lossy (unique)",
        "lowlevel-lossless": "Lossless (all)",
        "lowlevel-lossless-unique": "Lossless (unique)"
    }
    ret = []
    total_unique = {"key": "Total (unique)", "values": {}}
    total_all = {"key": "Total (all)", "values": {}}
    for val in cur:
        pairs = zip([_make_timestamp(v) for v in val[1]], val[2])
        ret.append({"key": stats_key_map.get(val[0], val[0]), "values": [{'x': v[0], 'y': v[1]} for v in pairs]})
        second = {}
        if val[0] in ["lowlevel-lossy", "lowlevel-lossless"]:
            second = total_all
        elif val[0] in ["lowlevel-lossy-unique", "lowlevel-lossless-unique"]:
            second = total_unique
        for pair in pairs:
            if pair[0] in second['values']:
                second['values'][pair[0]] = second['values'][pair[0]] + pair[1]
            else:
                second['values'][pair[0]] = pair[1]

    total_unique['values'] = [{'x': k, 'y': total_unique['values'][k]} for k in sorted(total_unique['values'].keys())]
    total_all['values'] = [{'x': k, 'y': total_all['values'][k]} for k in sorted(total_all['values'].keys())]
    ret.extend([total_unique, total_all])
    return ret


def _make_timestamp(dt):
    return time.mktime(dt.utctimetuple())*1000 + dt.microsecond/1000
