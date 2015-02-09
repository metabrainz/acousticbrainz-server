from flask import Blueprint, render_template
from flask_login import login_required

datasets_bp = Blueprint('datasets', __name__)


@datasets_bp.route('/create/', methods=('GET', 'POST'))
@login_required
def create():
    # TODO: Check if POST, validate data and save it.
    return render_template('datasets/create.html')
