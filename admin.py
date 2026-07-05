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
    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if not current_user.is_owner:
            abort(403)
        return view(*args, **kwargs)
    return wrapped


@admin_bp.route("/")
@admin_required
def panel():
    users = User.query.order_by(User.created_at.desc()).all()
    real_admins = sum(1 for u in users if u.role in ("admin", "owner"))

    if current_user.is_owner:
        # The owner sees the truth and can manage everyone.
        return render_template(
            "admin.html", is_owner=True, users=users,
            total_users=len(users), total_admins=real_admins,
        )

    # A plain admin sees only the summary, with the fixed admin count.
    return render_template(
        "admin.html", is_owner=False, users=None,
        total_users=None, total_admins=ADMIN_VISIBLE_ADMIN_COUNT,
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
                flash("That email is already used by another account.", "error")
                return render_template("edit_user.html", user=user), 400
            user.email = new_email
        new_role = request.form.get("role", user.role)
        if new_role in ("user", "admin", "owner"):
            user.role = new_role
        db.session.commit()
        flash("User updated.", "message")
        return redirect(url_for("admin.panel"))

    return render_template("edit_user.html", user=user)


@admin_bp.route("/users/<int:user_id>/delete", methods=["POST"])
@owner_required
def delete_user(user_id):
    user = db.session.get(User, user_id)
    if user is None:
        abort(404)
    if user.id == current_user.id:
        flash("You cannot delete your own owner account.", "error")
        return redirect(url_for("admin.panel"))
    db.session.delete(user)
    db.session.commit()
    flash("User deleted.", "message")
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
        "Prefetch interval (min)": current_app.config["PREFETCH_MINUTES"],
    }
    return render_template("diagnostics.html", tests=tests, state=state)
