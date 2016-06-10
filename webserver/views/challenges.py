from __future__ import absolute_import
from flask import Blueprint, render_template, request, redirect, url_for, jsonify
from flask_login import login_required
from werkzeug.exceptions import NotFound, BadRequest
from datetime import datetime
from math import ceil
import db.challenge
import db.exceptions
import pytz

challenges_bp = Blueprint('challenges', __name__)


@challenges_bp.route("/")
def index():
    content_filter = request.args.get("content_filter", default="all")
    if content_filter not in ["all", "upcoming", "active", "ended"]:
        raise BadRequest("Invalid filter.")
    page = int(request.args.get("page", default=1))
    if page < 1:
        return redirect(url_for('.index'))
    limit = 25
    offset = (page - 1) * limit
    challenges, total_count = db.challenge.list_all(
        content_filter=content_filter,
        limit=limit,
        offset=offset
    )
    last_page = int(ceil(total_count / limit))
    if last_page != 0 and page > last_page:
        return redirect(url_for('.index', content_filter=content_filter, page=last_page))
    return render_template("challenges/index.html",
                           challenges=challenges,
                           content_filter=content_filter,
                           page=page,
                           last_page=last_page)


@challenges_bp.route("/active-suggest")
@login_required
def active_suggest():
    query = request.args.get("q")
    if not query:
        raise BadRequest("Query is missing.")
    challenges = []
    for challenge in db.challenge.find_active(query):
        challenges.append({
            "id": challenge["id"],
            "name": challenge["name"],
        })

    return jsonify(challenges=challenges)


@challenges_bp.route("/<uuid:id>")
def details(id):
    try:
        challenge = db.challenge.get(id)
        # TODO: Implement pagination for submissions
    except db.exceptions.NoDataFoundException as e:
        raise NotFound(e)

    if challenge["start_time"] > datetime.now(pytz.utc):
        # Challenge hasn't begun yet.
        return render_template("challenges/details/upcoming.html",
                               challenge=challenge)
    elif not challenge["concluded"]:
        # Challenge is still ongoing (either deadline hasn't passed yet or there are unevaluated submissions).
        return render_template("challenges/details/ongoing.html",
                               challenge=challenge,
                               submissions=db.challenge.get_submissions(challenge["id"], order="submission"),
                               past_deadline=challenge["end_time"] < datetime.now(pytz.utc))
    else:
        # Challenge has concluded.
        # TODO: Get all submissions and sort them by accuracy.
        return render_template("challenges/details/concluded.html",
                               challenge=challenge,
                               submissions=db.challenge.get_submissions(challenge["id"], order="accuracy"))
