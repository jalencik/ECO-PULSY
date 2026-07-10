"""EcoPulse — air quality and weather monitoring for Uzbekistan.

Application factory and entry point.
"""
import gzip
import json
import os
import secrets
from datetime import datetime
from io import BytesIO
from pathlib import Path

import click
from flask import Flask, abort, g, render_template, request, session
from sqlalchemy import text
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.security import generate_password_hash

from config import Config
from extensions import cache, db, login_manager, scheduler
from services.regions import REGIONS, region_display_name
from translations import DEFAULT_LANG, LANG_LABELS, SUPPORTED_LANGS, t as translate


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
    _configure_compression(app)
    _configure_i18n(app)
    _configure_static_cache_busting(app)
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
        _promote_queen(app)      # make QUEEN_EMAIL the queen
        try:
            _seed_locations()
        except Exception:
            # Never block boot on seeding — the CLI command can retry it.
            db.session.rollback()
        try:
            _seed_fake_members()
        except Exception:
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
        # News thumbnails come from whatever CDN each article's source
        # site uses - an unpredictable set of third-party domains - so
        # image-src is opened to any HTTPS host rather than a fixed list.
        "img-src 'self' data: https:; "
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


def _configure_i18n(app):
    """English / Uzbek language switching.

    The choice lives in a plain "lang" cookie (no account change needed)
    and is exposed to every template as t()/lang/rname()/year, so most
    translation work is a template-only change. See translations.py.
    """

    @app.before_request
    def set_language():
        lang = request.cookies.get("lang")
        g.lang = lang if lang in SUPPORTED_LANGS else DEFAULT_LANG

    @app.context_processor
    def inject_i18n():
        lang = getattr(g, "lang", DEFAULT_LANG)
        return {
            "lang": lang,
            "t": lambda key, **kw: translate(lang, key, **kw),
            "rname": lambda region: region_display_name(region, lang),
            "supported_langs": SUPPORTED_LANGS,
            "lang_labels": LANG_LABELS,
            "year": datetime.now().year,
        }


def _configure_compression(app):
    """Gzip HTML/CSS/JS/JSON responses (stdlib only — no new dependency).

    Render's free tier does not compress responses for you, and a good
    share of traffic here is on phones over mobile data, so shrinking
    every text response meaningfully speeds up page loads. Static files
    served with send_file, images and streamed responses are untouched
    (direct_passthrough guards that).
    """
    compressible = {
        "text/html", "text/css", "text/plain", "text/xml",
        "application/json", "application/javascript", "text/javascript",
        "image/svg+xml",
    }

    @app.after_request
    def gzip_response(response):
        if response.direct_passthrough or "Content-Encoding" in response.headers:
            return response
        if not (200 <= response.status_code < 300):
            return response
        if "gzip" not in request.headers.get("Accept-Encoding", "").lower():
            return response
        if response.mimetype not in compressible:
            return response
        data = response.get_data()
        if len(data) < 500:  # tiny payloads: gzip overhead isn't worth it
            return response
        buffer = BytesIO()
        with gzip.GzipFile(mode="wb", fileobj=buffer, compresslevel=6) as gz:
            gz.write(data)
        response.set_data(buffer.getvalue())
        response.headers["Content-Encoding"] = "gzip"
        response.headers["Vary"] = "Accept-Encoding"
        return response


def _configure_static_cache_busting(app):
    """Make every `url_for('static', filename=...)` carry a `?v=<mtime>`.

    /static/* is served with a week-long browser Cache-Control (see
    SEND_FILE_MAX_AGE_DEFAULT in config.py) so repeat visits don't
    re-download unchanged CSS/JS - good for speed, but it also means a
    phone that already cached, say, static/js/map.js could keep serving
    that week-old copy for up to 7 days after a deploy that fixed a bug
    in it, even across normal page loads. Appending the file's own last-
    modified time to the URL makes a changed file get a brand new URL the
    instant it changes, so the stale cache entry is simply never reused -
    the browser fetches the new file immediately, no waiting out the
    week, no manual hard-refresh needed. Unchanged files keep the same
    URL and stay cached exactly as before.
    """

    @app.url_defaults
    def add_static_version(endpoint, values):
        if endpoint != "static" or "filename" not in values:
            return
        path = os.path.join(app.static_folder, values["filename"])
        try:
            values["v"] = int(os.path.getmtime(path))
        except OSError:
            pass


# Columns added after the users table already existed in production.
# db.create_all() never ALTERs existing tables, so we add them by hand,
# once, ignoring "already exists" errors. Safe on PostgreSQL and SQLite.
_NEW_USER_COLUMNS = {
    "birthdate": "VARCHAR(20)",
    "photo": "TEXT",
    "latitude": "DOUBLE PRECISION",
    "longitude": "DOUBLE PRECISION",
    "location_label": "VARCHAR(80)",
    # Marks the seeded demo accounts (see _seed_fake_members). The
    # NOT NULL DEFAULT FALSE backfills every existing real row to False
    # in the same statement, so this is never NULL for anyone.
    "is_fake": "BOOLEAN NOT NULL DEFAULT FALSE",
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


def _promote_queen(app):
    """Ensure the configured QUEEN_EMAIL holds the 'queen' role.

    Safety net for an account that already existed under a different
    role before QUEEN_EMAIL was set/changed - normal registrations are
    already assigned "queen" immediately in auth.py.
    """
    from models import User

    email = app.config.get("QUEEN_EMAIL", "")
    if not email:
        return
    try:
        user = User.query.filter_by(email=email).first()
        if user is not None and user.role not in ("owner", "queen"):
            user.role = "queen"
            db.session.commit()
    except Exception:
        db.session.rollback()


def _seed_locations():
    """Load data/districts.json into the locations table.

    Purely additive: only inserts (region, district) pairs from the
    dataset that aren't already in the table, and never touches or
    deletes an existing row. That matters because /locations/<id> is a
    plain numeric id with no stable natural key of its own - resyncing
    by wipe-and-recreate would silently change what id every existing
    district points to. Additive-only means a dataset fix (like adding
    a missing district) reaches an already-seeded production database
    on the next normal redeploy, safely.
    """
    from models import Location

    dataset = Path(__file__).parent / "data" / "districts.json"
    if not dataset.exists():
        return 0

    data = json.loads(dataset.read_text(encoding="utf-8"))
    existing = {(row.region_name, row.district_name) for row in Location.query.all()}

    count = 0
    for region_name, districts in data.items():
        for district in districts:
            key = (region_name, district["name"])
            if key in existing:
                continue
            db.session.add(Location(
                region_name=region_name,
                district_name=district["name"],
                latitude=district["lat"],
                longitude=district["lon"],
            ))
            existing.add(key)
            count += 1
    db.session.commit()
    return count


def _seed_fake_members():
    """Top the users table up to TARGET_TOTAL_USERS with clearly-marked
    demo member accounts, resyncing them whenever the generator in
    services/fake_members.py changes.

    These are NOT real people:
    - role is always "user" and is_fake is always True
    - the password is a random value generated and discarded on the
      spot, so the account can never be used to sign in
    - admin.py filters is_fake accounts out entirely for plain admins
      (real count and rows only); the owner and the Queen fold them
      into the combined total instead.

    The batch size is computed, not fixed: real (is_fake=False) rows
    are counted first and only the gap up to TARGET_TOTAL_USERS is
    generated, so the combined total always lands on the same round
    number no matter how many real people have registered.

    A one-row marker in the snapshots table records which
    fake_members.DATASET_VERSION is currently live. On boot, if that
    doesn't match the version in code, every is_fake row is deleted and
    regenerated from scratch - this is how a generator change (bigger,
    more diverse name/email pools) actually reaches an already-seeded
    production database instead of being silently skipped forever.
    Real user rows (is_fake=False) are never touched or deleted.
    """
    from models import Snapshot, User
    from services.fake_members import (DATASET_VERSION, TARGET_TOTAL_USERS,
                                       generate_fake_members)

    marker = db.session.get(Snapshot, "fake_members_version")
    up_to_date = marker is not None and marker.payload.get("version") == DATASET_VERSION
    if up_to_date and User.query.filter_by(is_fake=True).first() is not None:
        return 0

    # Wipe any previous batch (old repetitive names, older seed, etc.)
    # before regenerating so this stays a clean resync, not an add-on.
    User.query.filter_by(is_fake=True).delete(synchronize_session=False)

    real_count = User.query.filter_by(is_fake=False).count()
    needed = max(0, TARGET_TOTAL_USERS - real_count)

    existing_emails = {row[0] for row in db.session.query(User.email).all()}
    count = 0
    for person in generate_fake_members(needed):
        if person["email"] in existing_emails:
            continue
        user = User(
            name=person["name"], email=person["email"],
            birthdate=person["birthdate"], role="user", is_fake=True,
            created_at=person["created_at"],
        )
        # A random password nobody knows, hashed with a deliberately cheap
        # single-iteration PBKDF2. Real accounts get the strong default
        # (set_password); these accounts can never be signed into anyway
        # (the random password is discarded right here), and hashing 600+
        # of them with the expensive default would stall boot for minutes
        # - long enough to trip gunicorn's worker timeout on Render.
        user.password_hash = generate_password_hash(
            secrets.token_hex(16), method="pbkdf2:sha256:1")
        db.session.add(user)
        existing_emails.add(person["email"])
        count += 1

    if marker is None:
        db.session.add(Snapshot(key="fake_members_version", payload={"version": DATASET_VERSION}))
    else:
        marker.payload = {"version": DATASET_VERSION}

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
        return render_template("error.html", code=403, message="error.403"), 403

    @app.errorhandler(404)
    def not_found(_error):
        return render_template("error.html", code=404, message="error.404"), 404


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
        """Insert any districts from data/districts.json not already saved."""
        count = _seed_locations()
        click.echo(f"Inserted {count} new locations." if count else "Locations already up to date.")

    @app.cli.command("seed-fake-members")
    def seed_fake_members():
        """Insert or resync the demo member accounts (top-up to target total)."""
        count = _seed_fake_members()
        click.echo(f"Inserted {count} demo members." if count else "Demo members already up to date.")


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
