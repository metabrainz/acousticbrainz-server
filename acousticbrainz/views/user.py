from flask import Blueprint, render_template
from flask_login import login_required, current_user

user_bp = Blueprint('user', __name__)


@user_bp.route('/')
@login_required
def profile():
    return render_template('user/profile.html', user=current_user)
