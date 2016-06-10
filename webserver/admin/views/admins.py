from flask import request, url_for, redirect
from flask_admin import expose
from webserver.admin import AdminBaseView, forms
from webserver import flash
import db.user
import db.exceptions


class AdminsView(AdminBaseView):

    @expose("/")
    def index(self):
        return self.render("admin/admins/index.html",
                           admins=db.user.get_admins())

    @expose("/add", methods=["GET", "POST"])
    def add(self):
        form = forms.AddAdminForm()
        if form.validate_on_submit():
            try:
                db.user.set_admin(form.musicbrainz_id.data,
                                  admin=True,
                                  force=form.force.data)
                flash.success("Added an admin: %s." % form.musicbrainz_id.data)
            except db.exceptions.DatabaseException as e:
                flash.error("Error: %s" % e)
                return redirect(url_for(".add"))
            return redirect(url_for(".index"))
        return self.render("admin/admins/add.html", form=form)

    @expose("/remove")
    def remove(self):
        musicbrainz_id = request.args.get("musicbrainz_id")
        db.user.set_admin(musicbrainz_id, admin=False)
        flash.warning("Removed admin: %s." % musicbrainz_id)
        return redirect(url_for(".index"))

