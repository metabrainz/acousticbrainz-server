from __future__ import absolute_import
from flask import Blueprint, render_template, request, redirect, url_for
from db.submission_stats import get_last_submitted_recordings, get_stats_summary
from flask_login import login_required, current_user

from webserver import flash
import db.submission_stats
import db.user as db_user
import db.exceptions
from webserver.forms import GdprForm

index_bp = Blueprint('index', __name__)


@index_bp.route("/")
def index():
    stats, last_collected = get_stats_summary()
    last_collected_timestamp = 0
    if last_collected:
        last_collected_timestamp = db.submission_stats._make_timestamp(last_collected)
    return render_template("index/index.html", stats=stats, last_collected=last_collected,
                           last_submissions=get_last_submitted_recordings(),
                           last_collected_timestamp=last_collected_timestamp)


@index_bp.route('/agree-to-terms', methods=['GET', 'POST'])
@login_required
def gdpr_notice():
    form = GdprForm()
    if form.validate_on_submit():
        if form.preference.data == 'agree':
            try:
                db_user.agree_to_gdpr(current_user.musicbrainz_id)
            except db.exceptions.DatabaseException:
                flash.error('Could not store agreement to GDPR terms')
            next = request.form.get('next')
            if next:
                return redirect(next)
            return redirect(url_for('index.index'))
        elif form.preference.data == 'disagree':
            return redirect(url_for('login.logout', next=request.args.get('next')))
        else:
            flash.error('You must agree to or decline our terms')
            return render_template('index/gdpr.html', form=form, next=request.args.get('next'))
    else:
        return render_template('index/gdpr.html', form=form, next=request.args.get('next'))


@index_bp.route("/download")
def downloads():
    return render_template("index/downloads.html")


@index_bp.route("/contribute")
def contribute():
    return render_template("index/contribute.html")


@index_bp.route("/goals")
def goals():
    return render_template("index/goals.html")


@index_bp.route("/faq")
def faq():
    return render_template("index/faq.html")
