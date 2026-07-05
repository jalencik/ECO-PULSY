"""Authentication routes: register, login, logout."""
import re
import time

from flask import Blueprint, flash, redirect, render_template, request, url_for
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
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        problems = _validate_registration(name, email, password)
        if problems:
            for problem in problems:
                flash(problem, "error")
            return render_template("register.html", name=name, email=email), 400

        user = User(name=name, email=email)
        user.set_password(password)
        # The very first account becomes the administrator; later admins
        # are promoted with the `flask create-admin` command.
        if User.query.count() == 0:
            user.role = "admin"
        db.session.add(user)
        db.session.commit()

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
