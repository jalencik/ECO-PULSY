"""EcoPulse — air quality and weather monitoring for Uzbekistan.

Application factory and entry point.
"""
import json
import os
import secrets
from datetime import datetime
from pathlib import Path

import click
from flask import Flask, abort, render_template, request, session
from sqlalchemy import text
from werkzeug.middleware.proxy_fix import ProxyFix

from config import Config
from extensions import cache, db, login_manager, scheduler
from services.regions import REGIONS


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Render (like most PaaS) terminates HTTPS at a proxy; ProxyFix makes
    # Flask see the original scheme/host so secure cookies and url_for work.
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    db.init_app(app)
    cache.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please sign in to continue."

    from admin import admin_bp
    from auth import auth_bp
    from views import views_bp

    app.register_blueprint(views_bp)
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(admin_bp, url_prefix="/admin")

    _configure_csrf(app)
    _configure_security_headers(app)
    _register_error_pages(app)
    _register_cli(app)

    # Region list is needed by the sidebar on every page.
    app.jinja_env.globals["REGIONS"] = REGIONS

    # Build any missing tables and seed reference data the moment the app
    # boots. Because this runs at import time inside an app context, it
    # works identically under `flask run` locally and Gunicorn on Render,
    # so a fresh Supabase database gets its schema automatically.
    with app.app_context():
        db.create_all()
        _ensure_user_columns()   # add new profile columns to an existing table
        _promote_owner(app)      # make OWNER_EMAIL the owner
        try:
            _seed_locations()
        except Exception:
            # Never block boot on seeding — the CLI command can retry it.
            db.session.rollback()

    _start_prefetch_scheduler(app)

    return app


def _start_prefetch_scheduler(app):
    """Warm the data cache now and every PREFETCH_MINUTES thereafter.

    The job runs in a background thread, so users never trigger (or wait
    for) external API calls — pages are always served from memory.
    """
    if app.config["DEMO_DATA"] or app.config.get("TESTING") or scheduler.running:
        return

    from services.openmeteo import warm_cache

    def prefetch():
        with app.app_context():
            try:
                warm_cache()
            except Exception:  # a failed refresh must never kill the thread
                app.logger.exception("Background prefetch failed")

    scheduler.init_app(app)
    scheduler.add_job(
        id="prefetch",
        func=prefetch,
        trigger="interval",
        minutes=app.config["PREFETCH_MINUTES"],
        next_run_time=datetime.now(),  # also run once immediately at boot
    )
    scheduler.start()


def _configure_security_headers(app):
    """Baseline security headers recommended by the OWASP checklist."""

    csp = (
        "default-src 'self'; "
        "script-src 'self' https://cdn.jsdelivr.net; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdn.jsdelivr.net; "
        "font-src https://fonts.gstatic.com; "
        "img-src 'self' data:; "
        "connect-src 'self'; "
        "frame-ancestors 'none'"
    )

    @app.after_request
    def set_security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Content-Security-Policy", csp)
        if os.environ.get("RENDER"):  # HTTPS-only host -> enforce HSTS
            response.headers.setdefault(
                "Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        return response


# Columns added after the users table already existed in production.
# db.create_all() never ALTERs existing tables, so we add them by hand,
# once, ignoring "already exists" errors. Safe on PostgreSQL and SQLite.
_NEW_USER_COLUMNS = {
    "birthdate": "VARCHAR(20)",
    "photo": "TEXT",
    "latitude": "DOUBLE PRECISION",
    "longitude": "DOUBLE PRECISION",
    "location_label": "VARCHAR(80)",
}


def _ensure_user_columns():
    dialect = db.engine.dialect.name
    for name, col_type in _NEW_USER_COLUMNS.items():
        col_type_sql = col_type
        if dialect == "sqlite" and col_type == "DOUBLE PRECISION":
            col_type_sql = "FLOAT"
        try:
            if dialect == "postgresql":
                db.session.execute(text(
                    f"ALTER TABLE users ADD COLUMN IF NOT EXISTS {name} {col_type_sql}"))
            else:
                db.session.execute(text(
                    f"ALTER TABLE users ADD COLUMN {name} {col_type_sql}"))
            db.session.commit()
        except Exception:
            db.session.rollback()  # column already present — fine


def _promote_owner(app):
    """Ensure the configured OWNER_EMAIL holds the 'owner' role."""
    from models import User

    email = app.config.get("OWNER_EMAIL", "")
    if not email:
        return
    try:
        user = User.query.filter_by(email=email).first()
        if user is not None and user.role != "owner":
            user.role = "owner"
            db.session.commit()
    except Exception:
        db.session.rollback()


def _seed_locations():
    """Load data/districts.json into the locations table (idempotent).

    Runs only when the table is empty, so restarts and redeploys are safe
    and the 173 districts are inserted exactly once.
    """
    from models import Location

    if Location.query.count() > 0:
        return 0

    dataset = Path(__file__).parent / "data" / "districts.json"
    if not dataset.exists():
        return 0

    data = json.loads(dataset.read_text(encoding="utf-8"))
    count = 0
    for region_name, districts in data.items():
        for district in districts:
            db.session.add(Location(
                region_name=region_name,
                district_name=district["name"],
                latitude=district["lat"],
                longitude=district["lon"],
            ))
            count += 1
    db.session.commit()
    return count


def _configure_csrf(app):
    """Small session-token CSRF protection for all form posts."""

    @app.before_request
    def verify_csrf_token():
        if request.method == "POST":
            token = session.get("_csrf_token")
            sent = request.form.get("_csrf_token") or request.headers.get("X-CSRFToken")
            if not token or token != sent:
                abort(400, description="Invalid or missing CSRF token.")

    def csrf_token():
        if "_csrf_token" not in session:
            session["_csrf_token"] = secrets.token_hex(32)
        return session["_csrf_token"]

    app.jinja_env.globals["csrf_token"] = csrf_token


def _register_error_pages(app):
    @app.errorhandler(403)
    def forbidden(_error):
        return render_template("error.html", code=403,
                               message="You do not have permission to view this page."), 403

    @app.errorhandler(404)
    def not_found(_error):
        return render_template("error.html", code=404,
                               message="The page you are looking for does not exist."), 404


def _register_cli(app):
    @app.cli.command("create-admin")
    @click.argument("email")
    def create_admin(email):
        """Promote an existing user to administrator."""
        from models import User

        user = User.query.filter_by(email=email.lower()).first()
        if user is None:
            click.echo(f"No user found with email {email}. Ask them to register first.")
            return
        user.role = "admin"
        db.session.commit()
        click.echo(f"{user.name} ({user.email}) is now an administrator.")

    @app.cli.command("seed-locations")
    def seed_locations():
        """Insert the 173-district dataset (skips if already seeded)."""
        count = _seed_locations()
        click.echo(f"Inserted {count} locations." if count else "Locations already seeded.")


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
