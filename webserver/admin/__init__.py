from flask_admin import BaseView, AdminIndexView as IndexView
from flask_admin.contrib.sqla import ModelView
from flask_login import current_user
from flask import request, redirect, url_for


class AuthMixin(object):
    """All admin views that shouldn't be available to public must subclass this."""

    def is_accessible(self):
        return current_user.is_authenticated and current_user.admin

    def _handle_view(self, name, **kwargs):
        if not self.is_accessible():
            return redirect(url_for('login.index', next=request.url))


class AdminBaseView(AuthMixin, BaseView): pass
class AdminModelView(AuthMixin, ModelView): pass
class AdminIndexView(AuthMixin, IndexView): pass
