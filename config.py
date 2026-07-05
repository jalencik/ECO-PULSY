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

    # --- Caching & background prefetch -------------------------------
    # The scheduler refreshes data every PREFETCH_MINUTES; cached entries
    # live slightly longer (CACHE_TTL_SECONDS) so users are always served
    # instantly from memory and never wait on an external API call.
    CACHE_TYPE = "SimpleCache"
    CACHE_DEFAULT_TIMEOUT = 2400
    CACHE_TTL_SECONDS = int(os.environ.get("CACHE_TTL_SECONDS", 2400))

    # WeatherAPI.com key (weather + air quality). Set in Render -> Environment.
    WEATHERAPI_KEY = os.environ.get("WEATHERAPI_KEY", "")

    # The single account that outranks admins. On boot this user is
    # promoted to the "owner" role automatically.
    OWNER_EMAIL = os.environ.get("OWNER_EMAIL", "jaloliddin2009applicant@gmail.com").lower()

    # Max uploaded profile photo size (bytes) before rejecting.
    MAX_PHOTO_BYTES = int(os.environ.get("MAX_PHOTO_BYTES", 800_000))
    PREFETCH_MINUTES = int(os.environ.get("PREFETCH_MINUTES", 30))
    SCHEDULER_API_ENABLED = False

    # --- Session cookie hardening -------------------------------------
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    # Render sets the RENDER env var; only send cookies over HTTPS there
    # (keeping plain HTTP working for local development).
    SESSION_COOKIE_SECURE = bool(os.environ.get("RENDER"))

    # Set DEMO_DATA=1 to run without internet access (development only).
    # The UI clearly labels demo data so it can never be mistaken for real.
    DEMO_DATA = os.environ.get("DEMO_DATA") == "1"
