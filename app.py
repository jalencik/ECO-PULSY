"""EcoPulse — air quality and weather monitoring for Uzbekistan.

Application factory and entry point.
"""
import json
import secrets
from pathlib import Path

import click
from flask import Flask, abort, render_template, request, session

from config import Config
from extensions import db, login_manager
from services.regions import REGIONS


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
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
        try:
            _seed_locations()
        except Exception:
            # Never block boot on seeding — the CLI command can retry it.
            db.session.rollback()

    return app


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
            if not token or token != request.form.get("_csrf_token"):
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
