from __future__ import absolute_import
from flask import Blueprint, Response, render_template
from db.submission_stats import get_statistics_history
from operator import itemgetter
import json

stats_bp = Blueprint('stats', __name__)


@stats_bp.route("/statistics-graph")
def graph():
    return render_template("stats/statistics-graph.html")


@stats_bp.route("/statistics-data")
def data():
    return Response(json.dumps(sorted(get_statistics_history(), key=itemgetter('name'), reverse=True)),
                    content_type='application/json; charset=utf-8')
