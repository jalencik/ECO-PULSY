"""Administrator panel."""
import time
from functools import wraps

import requests
from flask import Blueprint, abort, current_app, render_template
from flask_login import current_user, login_required

from extensions import cache, scheduler
from models import Snapshot, User

admin_bp = Blueprint("admin", __name__)


def admin_required(view):
    """Allow access only to logged-in administrators."""
    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if not current_user.is_admin:
            abort(403)
        return view(*args, **kwargs)
    return wrapped


@admin_bp.route("/")
@admin_required
def panel():
    users = User.query.order_by(User.created_at.desc()).all()
    total_admins = sum(1 for user in users if user.is_admin)
    return render_template(
        "admin.html",
        users=users,
        total_users=len(users),
        total_admins=total_admins,
    )


@admin_bp.route("/diagnostics")
@admin_required
def diagnostics():
    """Live health check: tests both external APIs from THIS server and
    shows the exact status/error, plus cache and scheduler state.

    This exists so 'live data unavailable' is never a mystery again —
    open this page on the deployed site and read the real reason.
    """
    from services.openmeteo import AIR_API, HEADERS, WEATHER_API

    tests = []
    for name, url, params in [
        ("Weather API", WEATHER_API,
         {"latitude": 41.31, "longitude": 69.28, "current": "temperature_2m"}),
        ("Air-quality API", AIR_API,
         {"latitude": 41.31, "longitude": 69.28, "current": "pm2_5"}),
    ]:
        started = time.perf_counter()
        try:
            r = requests.get(url, params=params, timeout=15, headers=HEADERS)
            tests.append({
                "name": name,
                "status": r.status_code,
                "ok": r.status_code == 200,
                "ms": int((time.perf_counter() - started) * 1000),
                "detail": r.text[:300],
            })
        except requests.RequestException as exc:
            tests.append({
                "name": name,
                "status": "no response",
                "ok": False,
                "ms": int((time.perf_counter() - started) * 1000),
                "detail": f"{type(exc).__name__}: {exc}",
            })

    state = {
        "Scheduler running": scheduler.running,
        "Overview cached in memory": cache.get("overview") is not None,
        "Database snapshots stored": Snapshot.query.count(),
        "Demo mode": current_app.config["DEMO_DATA"],
        "Prefetch interval (min)": current_app.config["PREFETCH_MINUTES"],
    }
    return render_template("diagnostics.html", tests=tests, state=state)
