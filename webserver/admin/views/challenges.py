from flask import url_for, redirect
from flask_login import current_user
from flask_admin import expose
from webserver.admin import AdminBaseView, forms
from webserver import flash
import db.user
import db.challenge
import db.exceptions


class ChallengesView(AdminBaseView):

    @expose("/")
    def index(self):
        return self.render("admin/challenges/index.html",
                           challenges=db.challenge.list_all())

    @expose("/create", methods=["GET", "POST"])
    def create(self):
        form = forms.EditChallengeForm()
        if form.validate_on_submit():
            id = db.challenge.create(
                user_id=current_user.id,
                name=form.name.data,
                start_time=form.start_time.data,
                end_time=form.end_time.data,
            )
            flash.success('Challenge "%s" has been created. ID: %s.' %
                          (form.name.data, id))
            return redirect(url_for(".index"))
        return self.render("admin/challenges/add.html", form=form)

    @expose("/<uuid:id>/modify", methods=["GET", "POST"])
    def modify(self, id):
        challenge = db.challenge.get(id)
        form = forms.EditChallengeForm(
            default_name=challenge["name"],
            default_start_time=challenge["start_time"],
            default_end_time=challenge["end_time"],
        )
        if form.validate_on_submit():
            db.challenge.update(
                id=id,
                name=form.name.data,
                start_time=form.start_time.data,
                end_time=form.end_time.data,
            )
            flash.success('Challenge "%s" has been updated.' % form.name.data)
            return redirect(url_for(".index"))
        return self.render("admin/challenges/modify.html", form=form)

    @expose("/<uuid:id>/delete")
    def delete(self, id):
        challenge = db.challenge.get(id)
        if challenge["creator"] != current_user.id:
            flash.error("Only creator can delete this challenge.")
        else:
            db.challenge.delete(id)
            flash.warning('Challenge "%s" has been deleted.' % challenge["name"])
        return redirect(url_for(".index"))

