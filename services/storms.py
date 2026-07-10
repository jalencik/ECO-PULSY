"""Uzbekistan storm / squall / dust-storm early warning.

Coastal hurricanes never reach landlocked Uzbekistan - what actually
destroys roofs, greenhouses and crops here are violent wind squalls
("kuchli dovul") and the saline dust storms blowing off the dried Aral
seabed (the Aralkum, now one of the planet's most active dust sources;
UNEP's December 2025 report named sand-and-dust storms the driver of
Uzbekistan's worst PM spikes). Both hazards are forecastable: squalls
announce themselves with sharp surface-pressure drops and extreme wind
gusts, dust events show up directly in aerosol forecasts.

Data source: Open-Meteo's forecast + air-quality APIs (free, keyless).
All 14 regions are fetched in TWO batched HTTP calls (both endpoints
accept comma-separated coordinate lists), cached for 30 minutes with the
same stale-fallback + database-snapshot pattern the weather service
uses, so the page never breaks and never hammers the API.

Thresholds are deliberately conservative and defensible:
- Wind gusts (km/h): >=90 red (damaging squall, ~25 m/s),
  >=62 orange (strong squall, ~17 m/s), >=40 yellow (fresh wind).
- Dust (ug/m3, Open-Meteo aerosol): >=500 red (severe dust storm),
  >=150 orange (dust event), >=50 yellow (elevated dust).
- A >=4 hPa pressure fall within 3 hours flags squall potential.
"""
import random
from datetime import datetime, timedelta, timezone

import requests
from flask import current_app

from extensions import cache
from services import snapshots
from services.regions import REGIONS

FORECAST_API = "https://api.open-meteo.com/v1/forecast"
DUST_API = "https://air-quality-api.open-meteo.com/v1/air-quality"
REQUEST_TIMEOUT = 20
CACHE_SECONDS = 1800
CACHE_KEY = "storms"
STALE_CACHE_KEY = "storms:stale"
SNAPSHOT_KEY = "storms"
HOURS_AHEAD = 24  # the alert window shown on the page

GUST_RED, GUST_ORANGE, GUST_YELLOW = 90, 62, 40
DUST_RED, DUST_ORANGE, DUST_YELLOW = 500, 150, 50
PRESSURE_DROP_FLAG = 4.0  # hPa fall within any 3-hour window

_TIER_RANK = {"green": 0, "yellow": 1, "orange": 2, "red": 3}


def get_storms():
    """Cached 24-hour squall / dust outlook for all 14 regions.

    Returns {"regions": [...], "summary": {...}, "error": bool,
    "stale": bool, "demo": bool}. Never raises: a failed refresh falls
    back to the last good result (memory, then database snapshot),
    otherwise a clearly-labelled error state.
    """
    if current_app.config["DEMO_DATA"]:
        return _demo_storms()

    cached = cache.get(CACHE_KEY)
    if cached is not None:
        return cached

    try:
        result = _fetch()
        cache.set(CACHE_KEY, result, timeout=CACHE_SECONDS)
        cache.set(STALE_CACHE_KEY, result, timeout=0)
        snapshots.save(SNAPSHOT_KEY, result)
        return result
    except Exception:
        current_app.logger.warning("Storm outlook refresh failed", exc_info=True)
        stale = cache.get(STALE_CACHE_KEY) or snapshots.load(SNAPSHOT_KEY)
        if stale is not None:
            stale = dict(stale)
            stale["stale"] = True
            cache.set(CACHE_KEY, stale, timeout=300)
            return stale
        empty = {"regions": [], "summary": None, "error": True, "stale": False, "demo": False}
        cache.set(CACHE_KEY, empty, timeout=300)
        return empty


def _fetch():
    lats = ",".join(str(r["lat"]) for r in REGIONS)
    lons = ",".join(str(r["lon"]) for r in REGIONS)

    weather = requests.get(FORECAST_API, timeout=REQUEST_TIMEOUT, params={
        "latitude": lats, "longitude": lons,
        "hourly": "wind_speed_10m,wind_gusts_10m,surface_pressure",
        "forecast_days": 2, "timezone": "UTC",
    })
    weather.raise_for_status()
    weather_data = _as_list(weather.json())

    dust_data = None
    try:
        dust = requests.get(DUST_API, timeout=REQUEST_TIMEOUT, params={
            "latitude": lats, "longitude": lons,
            "hourly": "dust", "forecast_days": 2, "timezone": "UTC",
        })
        dust.raise_for_status()
        dust_data = _as_list(dust.json())
    except Exception:
        # Dust is an enhancement, not a dependency: a wind-only outlook
        # is still a real outlook. Rows simply show dust as unknown.
        current_app.logger.warning("Dust forecast unavailable", exc_info=True)

    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:00")
    rows = []
    for i, region in enumerate(REGIONS):
        w = weather_data[i] if i < len(weather_data) else {}
        d = dust_data[i] if dust_data and i < len(dust_data) else None
        rows.append(_analyse_region(region, w, d, now_iso))

    rows.sort(key=lambda r: (-_TIER_RANK[r["tier"]], -(r["peak_gust"] or 0)))
    return {
        "regions": rows,
        "summary": _summarise(rows),
        "error": False, "stale": False, "demo": False,
    }


def _as_list(payload):
    """Open-Meteo returns a dict for one location, a list for several."""
    return payload if isinstance(payload, list) else [payload]


def _analyse_region(region, weather, dust, now_iso):
    hourly = weather.get("hourly") or {}
    times = hourly.get("time") or []
    start = _first_index_at_or_after(times, now_iso)
    window = slice(start, start + HOURS_AHEAD)

    gusts = _clean(hourly.get("wind_gusts_10m"), window)
    winds = _clean(hourly.get("wind_speed_10m"), window)
    pressures = _clean(hourly.get("surface_pressure"), window)

    peak_gust = round(max(gusts)) if gusts else None
    peak_wind = round(max(winds)) if winds else None

    pressure_drop = 0.0
    for j in range(len(pressures) - 3):
        pressure_drop = max(pressure_drop, pressures[j] - pressures[j + 3])
    pressure_drop = round(pressure_drop, 1)

    peak_dust = None
    if dust is not None:
        d_hourly = dust.get("hourly") or {}
        d_start = _first_index_at_or_after(d_hourly.get("time") or [], now_iso)
        dust_values = _clean(d_hourly.get("dust"), slice(d_start, d_start + HOURS_AHEAD))
        if dust_values:
            peak_dust = round(max(dust_values))

    tier = _worst_tier(peak_gust, peak_dust)
    return {
        "slug": region["slug"],
        "name": region["name"],
        "peak_gust": peak_gust,
        "peak_wind": peak_wind,
        "peak_dust": peak_dust,
        "pressure_drop": pressure_drop,
        "squall_signal": pressure_drop >= PRESSURE_DROP_FLAG and (peak_gust or 0) >= GUST_YELLOW,
        "dust_event": (peak_dust or 0) >= DUST_ORANGE,
        "tier": tier,
    }


def _first_index_at_or_after(times, now_iso):
    for i, t in enumerate(times):
        if t >= now_iso:
            return i
    return 0


def _clean(values, window):
    if not values:
        return []
    return [v for v in values[window] if v is not None]


def _gust_tier(gust):
    if gust is None:
        return "green"
    if gust >= GUST_RED:
        return "red"
    if gust >= GUST_ORANGE:
        return "orange"
    if gust >= GUST_YELLOW:
        return "yellow"
    return "green"


def _dust_tier(dust_value):
    if dust_value is None:
        return "green"
    if dust_value >= DUST_RED:
        return "red"
    if dust_value >= DUST_ORANGE:
        return "orange"
    if dust_value >= DUST_YELLOW:
        return "yellow"
    return "green"


def _worst_tier(gust, dust_value):
    g, d = _gust_tier(gust), _dust_tier(dust_value)
    return g if _TIER_RANK[g] >= _TIER_RANK[d] else d


def _summarise(rows):
    if not rows:
        return None
    counts = {"red": 0, "orange": 0, "yellow": 0, "green": 0}
    for r in rows:
        counts[r["tier"]] += 1
    with_gust = [r for r in rows if r["peak_gust"] is not None]
    with_dust = [r for r in rows if r["peak_dust"] is not None]
    worst_gust = max(with_gust, key=lambda r: r["peak_gust"]) if with_gust else None
    worst_dust = max(with_dust, key=lambda r: r["peak_dust"]) if with_dust else None
    level = rows[0]["tier"]  # rows are sorted worst-first
    return {
        "counts": counts,
        "level": level,
        "alert_regions": counts["red"] + counts["orange"] + counts["yellow"],
        "worst_gust": worst_gust and {"slug": worst_gust["slug"], "name": worst_gust["name"],
                                      "value": worst_gust["peak_gust"]},
        "worst_dust": worst_dust and {"slug": worst_dust["slug"], "name": worst_dust["name"],
                                      "value": worst_dust["peak_dust"]},
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    }


# ---------------------------------------------------------------------------
# Demo data (offline dev only — always labelled in the UI)
# ---------------------------------------------------------------------------

def _demo_storms():
    rows = []
    for region in REGIONS:
        rng = random.Random("storm:" + region["slug"])
        gust = rng.randint(18, 96)
        dust_value = rng.choice([rng.randint(5, 45), rng.randint(60, 220), rng.randint(300, 650)])
        drop = round(rng.uniform(0.2, 6.5), 1)
        rows.append({
            "slug": region["slug"], "name": region["name"],
            "peak_gust": gust, "peak_wind": max(10, gust - rng.randint(8, 25)),
            "peak_dust": dust_value, "pressure_drop": drop,
            "squall_signal": drop >= PRESSURE_DROP_FLAG and gust >= GUST_YELLOW,
            "dust_event": dust_value >= DUST_ORANGE,
            "tier": _worst_tier(gust, dust_value),
        })
    rows.sort(key=lambda r: (-_TIER_RANK[r["tier"]], -(r["peak_gust"] or 0)))
    return {"regions": rows, "summary": _summarise(rows),
            "error": False, "stale": False, "demo": True}
