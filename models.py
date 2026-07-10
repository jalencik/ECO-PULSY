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
    role = db.Column(db.String(10), nullable=False, default="user")  # user | admin | owner
    created_at = db.Column(
        db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    # Optional profile details (all nullable so existing rows stay valid).
    birthdate = db.Column(db.String(20), nullable=True)   # YYYY-MM-DD
    photo = db.Column(db.Text, nullable=True)             # base64 data URI
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    location_label = db.Column(db.String(80), nullable=True)

    # Marks the seeded demo accounts. Never True for a real registration -
    # only app.py's one-time _seed_fake_members() sets this. Admins never
    # see these rows at all; only the owner's panel folds them into the
    # combined total (see admin.py).
    is_fake = db.Column(db.Boolean, nullable=False, default=False)

    @property
    def is_owner(self) -> bool:
        return self.role == "owner"

    @property
    def is_queen(self) -> bool:
        return self.role == "queen"

    @property
    def is_owner_or_queen(self) -> bool:
        """Full management powers: edit/delete any user. See admin.py."""
        return self.role in ("owner", "queen")

    @property
    def is_admin(self) -> bool:
        # Owners and the Queen have every admin power too.
        return self.role in ("admin", "owner", "queen")

    @property
    def role_label(self) -> str:
        return {"owner": "Owner", "queen": "Queen", "admin": "Administrator"}.get(self.role, "Member")

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


class TreePledge(db.Model):
    """One 'I planted N trees' entry logged by a signed-in member.

    Powers the community counter on the /trees (Yashil Makon) page: the
    official national figures come from a curated dataset, while this
    table is EcoPulse's own contribution layer - real members logging
    the trees they actually planted. Counts are capped per submission
    in the view (1..1000) so a typo can't fabricate a forest.
    """

    __tablename__ = "tree_pledges"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"),
                        nullable=False, index=True)
    count = db.Column(db.Integer, nullable=False)
    region_slug = db.Column(db.String(40), nullable=True)
    created_at = db.Column(
        db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    user = db.relationship("User", backref=db.backref("tree_pledges", lazy="dynamic",
                                                      cascade="all, delete-orphan"))

    def __repr__(self) -> str:
        return f"<TreePledge {self.count} by user {self.user_id}>"
