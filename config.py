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

    # Currents API key (News section). Free tier: 1,000 requests/day.
    # Get one at currentsapi.services - the News sidebar item shows a
    # clear "not configured" state until this is set, it never fakes
    # articles. Set in Render -> Environment.
    CURRENTS_API_KEY = os.environ.get("CURRENTS_API_KEY", "")

    # NASA FIRMS map key (Wildfires section). Free, instant signup at
    # firms.modaps.eosdis.nasa.gov/api/map_key - the Wildfires sidebar
    # item shows a clear "not configured" state until this is set.
    FIRMS_MAP_KEY = os.environ.get("FIRMS_MAP_KEY", "")

    # The single account that outranks admins. On boot this user is
    # promoted to the "owner" role automatically.
    OWNER_EMAIL = os.environ.get("OWNER_EMAIL", "jaloliddin2009applicant@gmail.com").lower()

    # The single account promoted to "queen" - full owner-level edit/delete
    # powers and the combined (real + demo) user total, but sees the admin
    # count and other admins' ranks the same way a plain admin does.
    QUEEN_EMAIL = os.environ.get("QUEEN_EMAIL", "muratovvaa.m@gmail.com").lower()

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

    # --- Performance ---------------------------------------------------
    # Lets browsers cache /static/* (CSS/JS) instead of re-fetching them on
    # every page view. A week is a deliberate middle ground: a meaningful
    # speed-up on repeat visits (especially on phones/slower connections)
    # without risking months-long staleness after a future deploy.
    SEND_FILE_MAX_AGE_DEFAULT = int(os.environ.get("STATIC_CACHE_SECONDS", 604800))
