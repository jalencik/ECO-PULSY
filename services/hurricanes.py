"""Active/recent tropical cyclones via GDACS (free, no key required).

GDACS (Global Disaster Alert and Coordination System) is jointly run by
the European Commission's Joint Research Centre and the UN Office for
the Coordination of Humanitarian Affairs. Its event API needs no signup
or key - GDACS only asks that responses acknowledge it as the source,
which the attribution line on this page does (see hurricanes.html).

Chosen over the US National Hurricane Center for global coverage:
Uzbekistan-relevant awareness of a typhoon near Japan or a cyclone near
Central America matters as much as anything in the Atlantic, and NHC
only covers the Atlantic/Eastern Pacific. Response schema below was
verified against a live call to the endpoint, not assumed from docs
alone.
"""
from datetime import datetime, timedelta, timezone

import requests
from flask import current_app

from extensions import cache

API_URL = "https://www.gdacs.org/gdacsapi/api/events/geteventlist/SEARCH"
REQUEST_TIMEOUT = 15
CACHE_SECONDS = 1800
STALE_CACHE_KEY = "hurricanes:stale"
CACHE_KEY = "hurricanes"
LOOKBACK_DAYS = 45  # "recent/current" window, not GDACS's full history
MAX_STORMS = 20


def get_hurricanes():
    """Cached recent/active tropical cyclones, most recent first.

    Returns {"storms": [...], "error": bool, "stale": bool}. Never
    raises: a failed fetch falls back to the last good list, otherwise a
    clearly-labelled empty result - never invented storms.
    """
    cached = cache.get(CACHE_KEY)
    if cached is not None:
        return cached

    try:
        storms = _fetch()
        result = {"storms": storms, "error": False, "stale": False}
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
        empty = {"storms": [], "error": True, "stale": False}
        cache.set(CACHE_KEY, empty, timeout=300)
        return empty


def _fetch():
    today = datetime.now(timezone.utc).date()
    since = today - timedelta(days=LOOKBACK_DAYS)
    response = requests.get(
        API_URL, timeout=REQUEST_TIMEOUT,
        params={
            "eventlist": "TC",
            "alertlevel": "green;orange;red",
            "fromdate": since.isoformat(),
            "todate": today.isoformat(),
        },
    )
    response.raise_for_status()
    data = response.json()

    storms = []
    for feature in data.get("features", []) or []:
        props = feature.get("properties") or {}
        geom = feature.get("geometry") or {}
        coords = geom.get("coordinates")
        lat = lon = None
        if isinstance(coords, list) and len(coords) >= 2:
            lon, lat = coords[0], coords[1]

        severity = props.get("severitydata") or {}
        url_block = props.get("url") or {}

        storms.append({
            "id": props.get("eventid"),
            "name": props.get("eventname") or ("Tropical Cyclone #" + str(props.get("eventid") or "?")),
            "country": props.get("country") or None,
            "alert_level": (props.get("alertlevel") or "green").lower(),
            "from_date": _short_date(props.get("fromdate")),
            "to_date": _short_date(props.get("todate")),
            "sort_date": props.get("fromdate") or "",
            "severity_text": severity.get("severitytext"),
            "lat": lat,
            "lon": lon,
            # Falls back to the GDACS homepage on the rare malformed
            # feature missing its own report link, so the card is never
            # a dead link rendered as the literal text "None".
            "report_url": url_block.get("report") or "https://www.gdacs.org/",
        })

    storms.sort(key=lambda s: s["sort_date"], reverse=True)
    return storms[:MAX_STORMS]


def _short_date(raw):
    if not raw:
        return None
    return raw[:10]
