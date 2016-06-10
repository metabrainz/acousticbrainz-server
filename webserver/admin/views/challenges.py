from flask import url_for, redirect, request
from flask_login import current_user
from flask_admin import expose
from webserver.admin import AdminBaseView, forms
from webserver import flash
from werkzeug.exceptions import BadRequest
from math import ceil
import db.user
import db.challenge
import db.exceptions


class ChallengesView(AdminBaseView):

    @expose("/")
    def index(self):
        content_filter = request.args.get("content_filter", default="all")
        if content_filter not in ["all", "upcoming", "active", "ended"]:
            raise BadRequest("Invalid filter.")
        page = int(request.args.get("page", default=1))
        if page < 1:
            return redirect(url_for('.index'))
        limit = 30
        offset = (page - 1) * limit
        challenges, total_count = db.challenge.list_all(
            content_filter=content_filter,
            limit=limit,
            offset=offset
        )
        last_page = int(ceil(total_count / limit))
        if last_page != 0 and page > last_page:
            return redirect(url_for('.index', content_filter=content_filter, page=last_page))
        return self.render("admin/challenges/index.html",
                           challenges=challenges,
                           content_filter=content_filter,
                           page=page,
                           last_page=last_page)

    @expose("/create", methods=["GET", "POST"])
    def create(self):
        form = forms.AddChallengeForm()
        if form.validate_on_submit():
            try:
                id = db.challenge.create(
                    user_id=current_user.id,
                    name=form.name.data,
                    start_time=form.start_time.data,
                    end_time=form.end_time.data,
                    classes=form.classes.data.split(","),
                    validation_dataset_id=form.validation_dataset_id.data,
                )
            except db.exceptions.DatabaseException as e:
                flash.error("Error: %s" % e)
                return self.render("admin/challenges/add.html", form=form)
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

