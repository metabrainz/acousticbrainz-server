from flask import redirect, url_for
from flask_login import LoginManager, UserMixin, current_user
from functools import wraps
from werkzeug.exceptions import Unauthorized
import db.user

login_manager = LoginManager()
login_manager.login_view = 'login.index'


class User(UserMixin):

    def __init__(self, id, created, musicbrainz_id, admin):
        self.id = id
        self.created = created
        self.musicbrainz_id = musicbrainz_id
        self.admin = admin

    @classmethod
    def from_dbrow(cls, user):
        return User(
            id=user['id'],
            created=user['created'],
            musicbrainz_id=user['musicbrainz_id'],
            admin=user['admin'],
        )


@login_manager.user_loader
def load_user(user_id):
    user = db.user.get(user_id)
    if user:
        return User.from_dbrow(user)
    else:
        return None

@login_manager.request_loader
def load_user(request):
    key = request.headers.get("Authorization")
    user = None
    if key:
        parts = key.split(" ")
        if len(parts) == 2 and parts[0] == "Token":
            user = db.user.get_by_api_key(parts[1])
        else:
            raise Unauthorized
    if user:
        return User.from_dbrow(user)
    else:
        return None


def login_forbidden(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if current_user.is_anonymous is False:
            return redirect(url_for('index.index'))
        return f(*args, **kwargs)

    return decorated
