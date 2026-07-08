"""Administrator & Owner panel."""
import math
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

# The owner/queen table can have 600+ rows (300 real + 300 demo). Paginate
# it server-side instead of rendering every row on every load - the page
# was one of the slowest in the app before this.
PAGE_SIZE = 50


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
    at 2, and every OTHER administrator is shown as a plain Member, same
    as a plain admin would see them. Only two ranks are ever shown as
    truthfully special to her: the owner (always "Owner") and herself
    (always "Queen"). This intentionally mirrors the plain-admin branch
    below exactly, just with the combined total and manage powers added.

    Plain admins: demo accounts are filtered out of the query entirely
    (never appear, in the count or the table), admin count fixed at 2,
    herself/the owner/the queen shown as Administrator, everyone else
    as Member.

    The table itself is paginated (PAGE_SIZE rows/page) for everyone -
    totals (total_users, total_admins) always come from real COUNT
    queries against the full table, never from loading every row into
    Python first, regardless of which page you're looking at.
    """
    if current_user.is_owner:
        base_query = User.query
        total_admins = User.query.filter(User.role.in_(("admin", "owner", "queen"))).count()
    elif current_user.is_queen:
        base_query = User.query
        total_admins = ADMIN_VISIBLE_ADMIN_COUNT
    else:
        base_query = User.query.filter_by(is_fake=False)
        total_admins = ADMIN_VISIBLE_ADMIN_COUNT

    total_users = base_query.order_by(None).count()
    total_pages = max(1, math.ceil(total_users / PAGE_SIZE))
    page = max(1, min(request.args.get("page", 1, type=int) or 1, total_pages))

    page_users = (base_query.order_by(User.created_at.desc())
                  .offset((page - 1) * PAGE_SIZE).limit(PAGE_SIZE).all())

    if current_user.is_owner:
        rows = [{"user": u, "role_label": u.role_label, "badge": u.is_admin} for u in page_users]
    elif current_user.is_queen:
        rows = []
        for u in page_users:
            if u.is_owner:
                rows.append({"user": u, "role_label": "Owner", "badge": True})
            elif u.id == current_user.id:
                rows.append({"user": u, "role_label": "Queen", "badge": True})
            else:
                rows.append({"user": u, "role_label": "Member", "badge": False})
    else:
        rows = []
        for u in page_users:
            if u.id == current_user.id or u.is_owner or u.is_queen:
                rows.append({"user": u, "role_label": "Administrator", "badge": True})
            else:
                rows.append({"user": u, "role_label": "Member", "badge": False})

    return render_template(
        "admin.html",
        is_owner=current_user.is_owner,
        is_queen=current_user.is_queen,
        can_manage=current_user.is_owner_or_queen,
        rows=rows,
        total_users=total_users,
        total_admins=total_admins,
        page=page,
        total_pages=total_pages,
        start_index=(page - 1) * PAGE_SIZE,
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
        # A Queen can promote/demote between Member and Administrator only -
        # never create a second Queen or hand out Owner. Only the Owner can
        # assign those two ranks. An out-of-range value (including a Queen
        # trying to slip "owner"/"queen" through the form) is silently
        # ignored, same as any other invalid role has always been here.
        new_role = request.form.get("role", user.role)
        allowed_roles = ("user", "admin", "owner", "queen") if current_user.is_owner else ("user", "admin")
        if new_role in allowed_roles:
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
        "Wildfire key present": bool(current_app.config.get("FIRMS_MAP_KEY")),
        "Prefetch interval (min)": current_app.config["PREFETCH_MINUTES"],
    }
    return render_template("diagnostics.html", tests=tests, state=state)
