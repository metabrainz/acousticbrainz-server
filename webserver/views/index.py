from __future__ import absolute_import
from flask import Blueprint, render_template
from db.stats import get_last_submitted_recordings, get_stats_summary
import db.stats

index_bp = Blueprint('index', __name__)


@index_bp.route("/")
def index():
    stats, last_collected = get_stats_summary()
    last_collected_timestamp = 0
    if last_collected:
        last_collected_timestamp = db.stats._make_timestamp(last_collected)
    return render_template("index/index.html", stats=stats, last_collected=last_collected,
                           last_submissions=get_last_submitted_recordings(),
                           last_collected_timestamp=last_collected_timestamp)


@index_bp.route("/download")
def downloads():
    return render_template("index/downloads.html")


@index_bp.route("/contribute")
def contribute():
    return render_template("index/contribute.html")


@index_bp.route("/goals")
def goals():
    return render_template("index/goals.html")


@index_bp.route("/faq")
def faq():
    return render_template("index/faq.html")
