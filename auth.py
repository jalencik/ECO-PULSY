"""Authentication routes: register, login, logout."""
import base64
import re
import time

from flask import (Blueprint, current_app, flash, redirect, render_template,
                   request, url_for)
from flask_login import current_user, login_required, login_user, logout_user

from extensions import db
from models import User

auth_bp = Blueprint("auth", __name__)

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MIN_PASSWORD_LENGTH = 8

# --- Brute-force protection -------------------------------------------
# After MAX_ATTEMPTS wrong passwords for the same email, sign-in for that
# email is locked for LOCK_SECONDS. Kept in memory: simple and effective
# for a single-worker deployment.
MAX_ATTEMPTS = 5
LOCK_SECONDS = 600
_failed_logins = {}  # email -> {"count": int, "locked_until": float}

# Signup spam protection: at most N successful registrations per IP per
# hour. Generous on purpose: mobile carriers put thousands of users
# behind one shared IP (CGNAT), so a tight limit would block real people.
SIGNUPS_PER_HOUR = 25
_signups = {}  # ip -> [timestamps]


def _signup_allowed(ip: str) -> bool:
    now = time.time()
    window = [t for t in _signups.get(ip, []) if now - t < 3600]
    _signups[ip] = window
    return len(window) < SIGNUPS_PER_HOUR


def _record_signup(ip: str) -> None:
    _signups.setdefault(ip, []).append(time.time())


def _is_locked(email: str) -> bool:
    entry = _failed_logins.get(email)
    return bool(entry and entry.get("locked_until", 0) > time.time())


def _record_failure(email: str) -> None:
    entry = _failed_logins.setdefault(email, {"count": 0, "locked_until": 0})
    entry["count"] += 1
    if entry["count"] >= MAX_ATTEMPTS:
        entry["locked_until"] = time.time() + LOCK_SECONDS
        entry["count"] = 0


def _clear_failures(email: str) -> None:
    _failed_logins.pop(email, None)


ALLOWED_PHOTO_TYPES = {"image/png", "image/jpeg", "image/webp", "image/gif"}


def _read_photo(file_storage):
    """Turn an uploaded image into a base64 data URI, or return (None, error)."""
    if not file_storage or not file_storage.filename:
        return None, None
    data = file_storage.read()
    if len(data) > current_app.config["MAX_PHOTO_BYTES"]:
        return None, "Profile photo must be under 800 KB."
    mimetype = file_storage.mimetype or "image/png"
    if mimetype not in ALLOWED_PHOTO_TYPES:
        return None, "Photo must be a PNG, JPG, WEBP or GIF image."
    encoded = base64.b64encode(data).decode("ascii")
    return f"data:{mimetype};base64,{encoded}", None


def _validate_registration(name, email, password):
    """Return a list of human-readable problems (empty list = valid)."""
    problems = []
    if len(name) < 2:
        problems.append("Please enter your full name.")
    if not EMAIL_PATTERN.match(email):
        problems.append("Please enter a valid email address.")
    if len(password) < MIN_PASSWORD_LENGTH:
        problems.append(f"Password must be at least {MIN_PASSWORD_LENGTH} characters.")
    if User.query.filter_by(email=email).first():
        problems.append("An account with this email already exists.")
    return problems


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("views.dashboard"))

    if request.method == "POST":
        if not _signup_allowed(request.remote_addr or "?"):
            flash("Sign-ups from this network are temporarily paused for security. "
                  "Please try again a little later.", "error")
            return render_template("register.html"), 429

        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        birthdate = request.form.get("birthdate", "").strip() or None

        problems = _validate_registration(name, email, password)
        photo, photo_error = _read_photo(request.files.get("photo"))
        if photo_error:
            problems.append(photo_error)
        if problems:
            for problem in problems:
                flash(problem, "error")
            return render_template("register.html", name=name, email=email,
                                   birthdate=birthdate), 400

        user = User(name=name, email=email, birthdate=birthdate, photo=photo)
        user.set_password(password)
        # The configured owner always registers as owner; otherwise the
        # very first account becomes an administrator.
        if email == current_app.config.get("OWNER_EMAIL"):
            user.role = "owner"
        elif User.query.count() == 0:
            user.role = "admin"
        db.session.add(user)
        db.session.commit()
        _record_signup(request.remote_addr or "?")

        login_user(user)
        return redirect(url_for("views.dashboard"))

    return render_template("register.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("views.dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if _is_locked(email):
            flash("Too many failed attempts. Please try again in 10 minutes.", "error")
            return render_template("login.html", email=email), 429

        user = User.query.filter_by(email=email).first()
        if user is None or not user.check_password(password):
            _record_failure(email)
            flash("Incorrect email or password.", "error")
            return render_template("login.html", email=email), 401

        _clear_failures(email)
        login_user(user, remember=request.form.get("remember") == "on")
        return redirect(url_for("views.dashboard"))

    return render_template("login.html")


@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    return redirect(url_for("views.index"))
