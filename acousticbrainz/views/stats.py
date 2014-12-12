from flask import Blueprint, Response, render_template, current_app
from operator import itemgetter
import psycopg2
import json
import time

stats_bp = Blueprint('stats', __name__)


@stats_bp.route("/statistics-graph")
def statistics_graph():
    return render_template("statistics-graph.html")


@stats_bp.route("/statistics-data")
def statistics_data():
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
        pairs = zip([make_timestamp(v) for v in val[1]], val[2])
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
    return Response(json.dumps(sorted(ret, key=itemgetter('key'))), content_type='application/json; charset=utf-8')


def make_timestamp(dt):
    return time.mktime(dt.utctimetuple())*1000 + dt.microsecond/1000
