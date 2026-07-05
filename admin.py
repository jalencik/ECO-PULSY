"""Administrator panel."""
from functools import wraps

from flask import Blueprint, abort, render_template
from flask_login import current_user, login_required

from models import User

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
