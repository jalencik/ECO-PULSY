"""Database models."""
from datetime import datetime, timezone

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from extensions import db, login_manager


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(10), nullable=False, default="user")  # "user" | "admin"
    created_at = db.Column(
        db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def __repr__(self) -> str:  # helpful in the flask shell
        return f"<User {self.email} ({self.role})>"


@login_manager.user_loader
def load_user(user_id: str):
    return db.session.get(User, int(user_id))


class Location(db.Model):
    """One selectable district (or city area) with precise coordinates.

    Stored in the database rather than hardcoded in Python so the list
    can grow without code changes and the picker loads with one query.
    """

    __tablename__ = "locations"
    __table_args__ = (
        db.UniqueConstraint("region_name", "district_name", name="uq_region_district"),
    )

    id = db.Column(db.Integer, primary_key=True)
    region_name = db.Column(db.String(80), nullable=False, index=True)
    district_name = db.Column(db.String(80), nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)

    def __repr__(self) -> str:
        return f"<Location {self.district_name}, {self.region_name}>"


class Snapshot(db.Model):
    """Last successful API payload per cache key.

    The in-memory cache disappears whenever the server restarts; this
    table keeps the freshest good data in the database so users never
    see an empty page, even if the external API is rate-limiting us at
    boot time. (Schema matches the table already live in production.)
    """

    __tablename__ = "snapshots"

    key = db.Column(db.String(120), primary_key=True)
    payload = db.Column(db.JSON, nullable=False)
    updated_at = db.Column(
        db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self) -> str:
        return f"<Snapshot {self.key}>"
