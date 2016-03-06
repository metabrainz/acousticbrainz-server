from __future__ import absolute_import
from flask import Blueprint, render_template, jsonify
from flask_login import current_user
from werkzeug.exceptions import NotFound
import db.user
import db.dataset

user_bp = Blueprint("user", __name__)


@user_bp.route("/user/<musicbrainz_id>")
def profile(musicbrainz_id):
    own_page = current_user.is_authenticated and \
               current_user.musicbrainz_id.lower() == musicbrainz_id.lower()
    if own_page:
        user = current_user
        datasets = db.dataset.get_by_user_id(user.id, public_only=False)
    else:
        user = db.user.get_by_mb_id(musicbrainz_id)
        if user is None:
            raise NotFound("Can't find this user.")
        datasets = db.dataset.get_by_user_id(user["id"])

    return render_template("user/profile.html", own_page=own_page, user=user, datasets=datasets)


@user_bp.route("/user-info")
def info():
    """This endpoint is meant for use by JavaScript that runs in a browser.
    The idea is to simplify a way to find out if user is currently logged in
    and, if they are, what is their username.

    This removes the need to pass user info that is used only by our interface
    with output of API endpoints.

    Returns:
        JSON with "user" value, which is None if user is not logged in, and
        user info otherwise (ID, account creation time, MusicBrainz username).
    """
    if current_user.is_authenticated:
        user = {
            "id": current_user.id,
            "created": current_user.created,
            "musicbrainz_id": current_user.musicbrainz_id,
        }
    else:
        user = None
    return jsonify({"user": user})
