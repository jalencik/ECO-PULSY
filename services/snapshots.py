"""Durable last-known-good storage for data payloads.

Every successful Open-Meteo payload is written here (keyed by its cache
key). When a live refresh fails — rate limit, timeout, cold start — the
weather service reads the most recent snapshot back and serves it instead
of an error page. Because the table lives in Postgres (Supabase in
production) the data survives restarts and is shared across all workers.

Every function swallows database errors: persistence is a safety net, so
it must never itself become a new source of failures.
"""
from datetime import datetime, timezone

from flask import current_app

from extensions import db


def save(key, payload):
    """Store *payload* as the latest good snapshot for *key* (upsert)."""
    try:
        from models import Snapshot

        row = db.session.get(Snapshot, key)
        if row is None:
            db.session.add(Snapshot(key=key, payload=payload))
        else:
            row.payload = payload
            row.updated_at = datetime.now(timezone.utc)
        db.session.commit()
    except Exception:
        # Never let a persistence hiccup break a request or the prefetch job.
        db.session.rollback()
        current_app.logger.warning("Snapshot save failed for %s", key, exc_info=True)


def load(key):
    """Return a copy of the last good payload for *key*, or None."""
    try:
        from models import Snapshot

        row = db.session.get(Snapshot, key)
        if row is None or not isinstance(row.payload, dict):
            return None
        return dict(row.payload)
    except Exception:
        db.session.rollback()
        current_app.logger.warning("Snapshot load failed for %s", key, exc_info=True)
        return None
