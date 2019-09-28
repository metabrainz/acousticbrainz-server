from __future__ import absolute_import

from flask import Blueprint, jsonify, request
from flask import abort
import similarity.path
import similarity.exceptions
import db.exceptions
import random

bp_path = Blueprint('api_v1_path', __name__)

@bp_path.route("/similarity_path/<uuid:mbid_from>/<uuid:mbid_to>", methods=["GET"])
def generate_similarity_path(mbid_from, mbid_to):
    """Generate a path from one mbid to another taking the next most 
    similar track on the way to the final target

    :resheader Content-Type: *application/json*
    """
    steps = request.args.get("steps", "10")
    metric = "mfccs"
    try:
        steps = int(steps)
    except ValueError:
        steps = 10
    try:
        path, distances = similarity.path.get_path((mbid_from, 0), (mbid_to, 0), steps, metric)
    except db.exceptions.NoDataFoundException:
        abort(404)
    except IndexError:
        abort(404)
    except similarity.exceptions.SimilarityException:
        abort(404)

    return jsonify(path)
