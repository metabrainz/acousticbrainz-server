from __future__ import absolute_import
from flask import Blueprint, render_template, jsonify
from flask_login import current_user, login_required
from werkzeug.exceptions import NotFound
import db.user
import db.dataset
import db.api_key

user_bp = Blueprint("user", __name__)


@user_bp.route("/user/<musicbrainz_id>")
def profile(musicbrainz_id):
    own_page = current_user.is_authenticated and \
               current_user.musicbrainz_id.lower() == musicbrainz_id.lower()
    if own_page:
        api_keys = db.api_key.get_active(current_user.id)
        args = {
            "own_page": True,
            "user": current_user,
            "datasets": db.dataset.get_by_user_id(current_user.id, public_only=False),
            "api_key": api_keys[-1] if api_keys else None,
        }
    else:
        user = db.user.get_by_mb_id(musicbrainz_id)
        if user is None:
            raise NotFound("Can't find this user.")
        args = {
            "own_page": False,
            "user": user,
            "datasets": db.dataset.get_by_user_id(user["id"]),
        }

    return render_template("user/profile.html", **args)


@user_bp.route("/user/generate-api-key", methods=['POST'])
@login_required
def generate_api_key():
    """This endpoint revokes all keys owned by current user and generates a new one."""
    db.api_key.revoke_all(current_user.id)
    return jsonify({'key': db.api_key.generate(current_user.id)})


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
