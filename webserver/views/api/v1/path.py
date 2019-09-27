from __future__ import absolute_import

from flask import Blueprint, jsonify, request

bp_path = Blueprint('api_v1_path', __name__)

@bp_path.route("/similarity_path/<uuid:mbid_from>/<uuid:mbid_to>", methods=["GET"])
def generate_similarity_path(mbid_from, mbid_to):
    """Generate a path from one mbid to another taking the next most 
    similar track on the way to the final target

    :resheader Content-Type: *application/json*
    """
    data = {"mbid_from": mbid_from, "mbid_to": mbid_to}
    return jsonify(data)
