from flask import Blueprint, Response, render_template
from acousticbrainz.data import get_statistics_data
from operator import itemgetter
import json

stats_bp = Blueprint('stats', __name__)


@stats_bp.route("/statistics-graph")
def statistics_graph():
    return render_template("statistics-graph.html")


@stats_bp.route("/statistics-data")
def statistics_data():
    return Response(json.dumps(sorted(get_statistics_data(), key=itemgetter('key'))),
                    content_type='application/json; charset=utf-8')
