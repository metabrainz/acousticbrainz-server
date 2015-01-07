from flask import Blueprint, render_template
from acousticbrainz.data import get_last_submitted_tracks, get_stats

index_bp = Blueprint('index', __name__)


@index_bp.route("/")
def index():
    stats, last_collected = get_stats()
    return render_template("index.html", stats=stats, last_collected=last_collected,
                           last_submitted_data=get_last_submitted_tracks())


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
