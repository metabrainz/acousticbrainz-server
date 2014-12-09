from flask import Blueprint, render_template, current_app
import psycopg2
import datetime
import memcache

index_bp = Blueprint('index', __name__)


STATS_CACHE_TIMEOUT = 60 * 10  # ten minutes
LAST_MBIDS_CACHE_TIMEOUT = 60  # 1 minute (this query is cheap)


@index_bp.route("/")
def index():
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

    return render_template("index.html", stats=value, last_collected=last_collected, last_submitted_data=last_submitted_data)


@index_bp.route("/download")
def download():
    return render_template("download.html")


@index_bp.route("/contribute")
def contribute():
    return render_template("contribute.html")


@index_bp.route("/goals")
def goals():
    return render_template("goals.html")


@index_bp.route("/faq")
def faq():
    return render_template("faq.html")
