from __future__ import absolute_import
from flask import Blueprint, render_template
from werkzeug.exceptions import NotFound
import db.challenge
import db.exceptions

challenges_bp = Blueprint('challenges', __name__)


@challenges_bp.route("/")
def index():
    return render_template("challenges/index.html",
                           challenges=db.challenge.list_all())


@challenges_bp.route("/<uuid:id>")
def details(id):
    try:
        challenge = db.challenge.get(id)
    except db.exceptions.NoDataFoundException as e:
        raise NotFound(e)
    return render_template("challenges/details.html",
                           challenge=challenge)
