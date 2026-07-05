"""Application configuration.

All secrets come from environment variables so nothing sensitive
is ever committed to the repository.
"""
import os


def _normalise_database_url(url: str) -> str:
    """Make cloud Postgres URLs (Supabase, Heroku, Render) SQLAlchemy-safe.

    Providers hand out URLs starting with `postgres://`, but SQLAlchemy 2.x
    only accepts `postgresql://`. This one-line fix is the most common
    reason a Render + Supabase deployment fails on boot.
    """
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    return url


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-key-change-in-production")
    SQLALCHEMY_DATABASE_URI = _normalise_database_url(
        os.environ.get("DATABASE_URL", "sqlite:///ecopulse.db")
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # pool_pre_ping checks connections before use, which prevents the
    # "server closed the connection unexpectedly" errors that cloud
    # Postgres poolers (like Supabase's) cause after idle periods.
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}

    # How long fetched weather/air-quality data is reused before calling
    # the API again (seconds). Keeps us well inside free API limits.
    CACHE_TTL_SECONDS = int(os.environ.get("CACHE_TTL_SECONDS", 600))

    # Set DEMO_DATA=1 to run without internet access (development only).
    # The UI clearly labels demo data so it can never be mistaken for real.
    DEMO_DATA = os.environ.get("DEMO_DATA") == "1"
