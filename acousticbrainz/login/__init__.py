from flask import redirect, url_for
from flask_login import LoginManager, current_user
from acousticbrainz.data import user as user_data
from functools import wraps

login_manager = LoginManager()
login_manager.login_view = 'login.index'


@login_manager.user_loader
def load_user(user_id):
    return user_data.get(user_id)


def login_forbidden(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if current_user.is_anonymous() is False:
            return redirect(url_for('frontend.index'))
        return f(*args, **kwargs)

    return decorated
