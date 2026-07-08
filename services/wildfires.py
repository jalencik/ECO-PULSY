"""Active wildfire hotspots via NASA FIRMS (free, real satellite detections).

Chosen after researching wildfire data sources for this feature: FIRMS
(Fire Information for Resource Management System) is NASA's own
near-real-time active-fire product, built from VIIRS/MODIS satellite
passes - the same underlying data most real wildfire-tracking sites and
apps are built on. A free MAP_KEY is required (instant signup at
https://firms.modaps.eosdis.nasa.gov/api/map_key/) - the Wildfires
sidebar item shows a clear "not configured" state until FIRMS_MAP_KEY is
set, it never fabricates hotspots.

Global coverage (Uzbekistan itself sees relatively few large wildfires,
being mostly desert/steppe, so a Uzbekistan-only view would be nearly
always empty) - most recent 24 hours only, VIIRS S-NPP near-real-time
source (375m resolution, finer-grained than MODIS's 1km). Nominal/high
confidence detections only, cutting out the low-confidence "noise" the
raw feed includes; capped to the most intense (highest fire radiative
power) points so the map and list stay readable rather than trying to
show every one of what can be several thousand detections worldwide on
an average day - the true total is still shown as a headline number.
"""
import csv
import io

import requests
from flask import current_app

from extensions import cache

API_URL = "https://firms.modaps.eosdis.nasa.gov/api/area/csv/{key}/{source}/world/{days}"
REQUEST_TIMEOUT = 25
SOURCE = "VIIRS_SNPP_NRT"
DAY_RANGE = 1
CACHE_SECONDS = 1800  # FIRMS NRT itself only refreshes a handful of times a day
STALE_CACHE_KEY = "wildfires:stale"
CACHE_KEY = "wildfires"
MAX_POINTS = 250


def _api_key():
    return current_app.config.get("FIRMS_MAP_KEY", "")


def get_wildfires():
    """Cached recent high-confidence fire detections.

    Returns {"points": [...], "total": int, "error": bool, "stale": bool,
    "configured": bool}. "total" is the full high-confidence count before
    the MAX_POINTS cap, so the headline number is always the true count
    even though the map/list only render the most intense subset. Never
    raises: a failed fetch falls back to the last good list, otherwise a
    clearly-labelled empty result - never invented hotspots.
    """
    if not _api_key():
        return {"points": [], "total": 0, "error": False, "stale": False, "configured": False}

    cached = cache.get(CACHE_KEY)
    if cached is not None:
        return cached

    try:
        points, total = _fetch()
        result = {"points": points, "total": total, "error": False, "stale": False, "configured": True}
        cache.set(CACHE_KEY, result, timeout=CACHE_SECONDS)
        cache.set(STALE_CACHE_KEY, result, timeout=0)
        return result
    except Exception:
        stale = cache.get(STALE_CACHE_KEY)
        if stale is not None:
            stale = dict(stale)
            stale["stale"] = True
            cache.set(CACHE_KEY, stale, timeout=300)
            return stale
        empty = {"points": [], "total": 0, "error": True, "stale": False, "configured": True}
        cache.set(CACHE_KEY, empty, timeout=300)
        return empty


def _fetch():
    url = API_URL.format(key=_api_key(), source=SOURCE, days=DAY_RANGE)
    response = requests.get(url, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    text = response.text

    # FIRMS returns plain-text error messages (e.g. an invalid key) with
    # an HTTP 200 instead of an error status code - detect that instead
    # of trying to CSV-parse an error message as if it were hotspot data.
    first_line = text.splitlines()[0].lower() if text.strip() else ""
    if "latitude" not in first_line:
        raise ValueError("Unexpected FIRMS response: " + text[:200])

    reader = csv.DictReader(io.StringIO(text))
    rows = []
    for row in reader:
        confidence = (row.get("confidence") or "").strip().lower()
        if confidence not in ("n", "h", "nominal", "high"):
            continue
        try:
            rows.append({
                "lat": float(row["latitude"]),
                "lon": float(row["longitude"]),
                "frp": float(row["frp"]) if row.get("frp") else 0.0,
                "date": row.get("acq_date"),
                "time": (row.get("acq_time") or "").zfill(4),
                "confidence": confidence,
                "daynight": row.get("daynight"),
            })
        except (KeyError, ValueError):
            continue

    total = len(rows)
    rows.sort(key=lambda r: r["frp"], reverse=True)
    return rows[:MAX_POINTS], total
