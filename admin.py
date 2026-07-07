"""Administrator & Owner panel."""
import time
from functools import wraps

import requests
from flask import (Blueprint, abort, current_app, flash, redirect,
                   render_template, request, url_for)
from flask_login import current_user, login_required

from extensions import cache, db, scheduler
from models import Snapshot, User

admin_bp = Blueprint("admin", __name__)

# What admins (not the owner) are shown as the admin count, by request.
ADMIN_VISIBLE_ADMIN_COUNT = 2


def admin_required(view):
    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if not current_user.is_admin:
            abort(403)
        return view(*args, **kwargs)
    return wrapped


def owner_required(view):
    """Owner AND Queen both get full management powers (edit/delete)."""
    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if not current_user.is_owner_or_queen:
            abort(403)
        return view(*args, **kwargs)
    return wrapped


@admin_bp.route("/")
@admin_required
def panel():
    """Three-tier visibility.

    Owner: everyone's real role, the real admin count, and the combined
    (real + demo) total.

    Queen: the same combined total as the owner and the same edit/delete
    powers, but - like a plain admin - always sees the admin count fixed
    at 2, and every admin/queen other than herself is shown as a plain
    Administrator. The owner is always shown truthfully as Owner, and
    she is always shown truthfully as Queen.

    Plain admins: demo accounts are filtered out of the query entirely
    (never appear, in the count or the table), admin count fixed at 2,
    herself/the owner/the queen shown as Administrator, everyone else
    as Member.
    """
    if current_user.is_owner:
        users = User.query.order_by(User.created_at.desc()).all()
        rows = [{"user": u, "role_label": u.role_label, "badge": u.is_admin} for u in users]
        total_admins = sum(1 for u in users if u.is_admin)
    elif current_user.is_queen:
        users = User.query.order_by(User.created_at.desc()).all()
        rows = []
        for u in users:
            if u.is_owner:
                rows.append({"user": u, "role_label": "Owner", "badge": True})
            elif u.id == current_user.id:
                rows.append({"user": u, "role_label": "Queen", "badge": True})
            elif u.is_admin:
                rows.append({"user": u, "role_label": "Administrator", "badge": True})
            else:
                rows.append({"user": u, "role_label": "Member", "badge": False})
        total_admins = ADMIN_VISIBLE_ADMIN_COUNT
    else:
        users = (User.query.filter_by(is_fake=False)
                 .order_by(User.created_at.desc()).all())
        rows = []
        for u in users:
            if u.id == current_user.id or u.is_owner or u.is_queen:
                rows.append({"user": u, "role_label": "Administrator", "badge": True})
            else:
                rows.append({"user": u, "role_label": "Member", "badge": False})
        total_admins = ADMIN_VISIBLE_ADMIN_COUNT

    return render_template(
        "admin.html",
        is_owner=current_user.is_owner,
        is_queen=current_user.is_queen,
        can_manage=current_user.is_owner_or_queen,
        rows=rows,
        total_users=len(users),
        total_admins=total_admins,
    )


@admin_bp.route("/users/<int:user_id>/edit", methods=["GET", "POST"])
@owner_required
def edit_user(user_id):
    user = db.session.get(User, user_id)
    if user is None:
        abort(404)

    if request.method == "POST":
        user.name = request.form.get("name", user.name).strip()
        new_email = request.form.get("email", user.email).strip().lower()
        if new_email and new_email != user.email:
            if User.query.filter(User.email == new_email, User.id != user.id).first():
                flash("flash.email_in_use", "error")
                return render_template("edit_user.html", user=user), 400
            user.email = new_email
        new_role = request.form.get("role", user.role)
        if new_role in ("user", "admin", "owner", "queen"):
            user.role = new_role
        db.session.commit()
        flash("flash.user_updated", "message")
        return redirect(url_for("admin.panel"))

    return render_template("edit_user.html", user=user)


@admin_bp.route("/users/<int:user_id>/delete", methods=["POST"])
@owner_required
def delete_user(user_id):
    user = db.session.get(User, user_id)
    if user is None:
        abort(404)
    if user.id == current_user.id:
        flash("flash.cannot_delete_self", "error")
        return redirect(url_for("admin.panel"))
    if user.is_owner:
        # Now that Queen also has delete power, make sure nobody - not
        # even by mistake - can delete the one owner account.
        flash("flash.cannot_delete_owner", "error")
        return redirect(url_for("admin.panel"))
    db.session.delete(user)
    db.session.commit()
    flash("flash.user_deleted", "message")
    return redirect(url_for("admin.panel"))


@admin_bp.route("/diagnostics")
@admin_required
def diagnostics():
    """Live health check: tests WeatherAPI from THIS server and shows the
    exact status/error, plus cache and scheduler state."""
    from services.openmeteo import API_URL, HEADERS

    tests = []
    key = current_app.config.get("WEATHERAPI_KEY", "")
    if not key:
        tests.append({"name": "WeatherAPI (weather + AQI)", "status": "no key",
                      "ok": False, "ms": 0,
                      "detail": "WEATHERAPI_KEY is not set. Add it in Render -> Environment."})
    else:
        started = time.perf_counter()
        try:
            r = requests.get(API_URL, timeout=15, headers=HEADERS,
                             params={"key": key, "q": "41.31,69.28", "days": 1, "aqi": "yes"})
            tests.append({"name": "WeatherAPI (weather + AQI)", "status": r.status_code,
                          "ok": r.status_code == 200,
                          "ms": int((time.perf_counter() - started) * 1000),
                          "detail": r.text[:300]})
        except requests.RequestException as exc:
            tests.append({"name": "WeatherAPI (weather + AQI)", "status": "no response",
                          "ok": False, "ms": int((time.perf_counter() - started) * 1000),
                          "detail": f"{type(exc).__name__}: {exc}"})

    state = {
        "Scheduler running": scheduler.running,
        "Overview cached in memory": cache.get("overview") is not None,
        "Database snapshots stored": Snapshot.query.count(),
        "Demo mode": current_app.config["DEMO_DATA"],
        "Weather key present": bool(key),
        "News key present": bool(current_app.config.get("CURRENTS_API_KEY")),
        "Prefetch interval (min)": current_app.config["PREFETCH_MINUTES"],
    }
    return render_template("diagnostics.html", tests=tests, state=state)
