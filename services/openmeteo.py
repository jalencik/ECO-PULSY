"""Open-Meteo client for weather and air-quality data.

Design notes:
- Both APIs accept comma-separated coordinate lists, so the national
  overview (14 regions) costs exactly two HTTP requests.
- Responses are cached in memory for CACHE_TTL_SECONDS to stay far
  below the free-tier limits and to keep pages fast.
- If DEMO_DATA=1 the module returns clearly-labelled synthetic data,
  which allows offline development. Demo data is never shown as real.
"""
import random
import time
from datetime import datetime, timedelta

import requests
from flask import current_app

from extensions import cache
from services import snapshots
from services.aqi import pm25_to_aqi
from services.regions import REGIONS, get_region

WEATHER_API = "https://api.open-meteo.com/v1/forecast"
AIR_API = "https://air-quality-api.open-meteo.com/v1/air-quality"
REQUEST_TIMEOUT = 15

# Retry policy for transient failures (rate limits, 5xx, timeouts). Kept
# short so an inline request on a cold start never blocks a user for long —
# the snapshot layer covers the rare case where all retries still fail.
MAX_RETRIES = 3
BACKOFF_BASE = 1.0   # seconds; doubles each attempt
MAX_BACKOFF = 6.0    # cap on any single wait, incl. Retry-After

# WMO weather interpretation codes -> (human label, icon id in the SVG sprite)
WEATHER_CODES = {
    0: ("Clear sky", "sun"), 1: ("Mostly clear", "sun"),
    2: ("Partly cloudy", "sun-cloud"), 3: ("Overcast", "cloud"),
    45: ("Fog", "fog"), 48: ("Rime fog", "fog"),
    51: ("Light drizzle", "drizzle"), 53: ("Drizzle", "drizzle"), 55: ("Heavy drizzle", "drizzle"),
    56: ("Freezing drizzle", "drizzle"), 57: ("Freezing drizzle", "drizzle"),
    61: ("Light rain", "rain"), 63: ("Rain", "rain"), 65: ("Heavy rain", "rain"),
    66: ("Freezing rain", "rain"), 67: ("Freezing rain", "rain"),
    71: ("Light snow", "snow"), 73: ("Snow", "snow"), 75: ("Heavy snow", "snow"),
    77: ("Snow grains", "snow"),
    80: ("Light showers", "rain"), 81: ("Showers", "rain"), 82: ("Violent showers", "rain"),
    85: ("Snow showers", "snow"), 86: ("Snow showers", "snow"),
    95: ("Thunderstorm", "storm"), 96: ("Thunderstorm, hail", "storm"), 99: ("Thunderstorm, hail", "storm"),
}

def describe_weather(code):
    return WEATHER_CODES.get(code, ("Unknown", "cloud"))


def _cached(key, builder):
    """Return live data for *key*, never surfacing a bare error if avoidable.

    Order of preference:
    1. A warm in-memory value (the common case — the background job keeps
       it fresh, so users are served instantly).
    2. A freshly built value; on success it is cached and snapshotted.
    3. If the build fails, the last good snapshot from the database, served
       with ``stale=True`` so the page shows a gentle notice instead of the
       red error banner. This is what makes rate limits and cold starts
       invisible to users.
    4. Only when no snapshot has *ever* existed does the error propagate.
    """
    value = cache.get(key)
    if value is not None:
        return value

    value = builder()
    if not value.get("error"):
        cache.set(key, value, timeout=current_app.config["CACHE_TTL_SECONDS"])
        snapshots.save(key, value)
        return value

    stale = snapshots.load(key)
    if stale is not None:
        stale = {**stale, "error": False, "stale": True}
        # Cache the stale copy briefly so we retry the API soon, not on
        # every single request.
        cache.set(key, stale, timeout=60)
        return stale

    # Genuinely nothing to show — cache the error only briefly so it heals.
    cache.set(key, value, timeout=60)
    return value


def _store(key, value):
    """Persist a freshly built payload to memory and the snapshot table."""
    if value.get("error"):
        return
    cache.set(key, value, timeout=current_app.config["CACHE_TTL_SECONDS"])
    snapshots.save(key, value)


def warm_cache():
    """Prefetch the national overview and all 14 region pages.

    Runs in a background thread on a schedule, so every user request is
    served instantly from memory instead of waiting on external APIs.

    The 14 region detail pages are fetched in TWO batched requests (one
    weather, one air quality) instead of 28 individual ones, which keeps
    us well under Open-Meteo's per-IP rate limit on Render's shared
    outbound addresses. If the batch call fails we fall back to spaced-out
    individual requests so a partial outage still refreshes what it can.
    """
    overview = _build_overview()
    _store("overview", overview)

    details = _build_region_details_batch()
    if details is not None:
        for slug, detail in details.items():
            _store(f"detail:region:{slug}", detail)
        return

    for region in REGIONS:
        _store(f"detail:region:{region['slug']}", _build_detail(region["lat"], region["lon"]))
        time.sleep(0.5)  # gentle stagger on the fallback path


def _retry_after_seconds(response, default):
    """Seconds to wait, honoring a numeric Retry-After header when present."""
    header = response.headers.get("Retry-After")
    if header:
        try:
            return min(float(header), MAX_BACKOFF)
        except ValueError:
            pass  # HTTP-date form — fall back to our own backoff
    return default


def _get_json(url, params):
    """GET JSON, retrying transient failures with capped exponential backoff.

    Retries on connection errors, timeouts, HTTP 429 (rate limit) and 5xx.
    A 429 with a Retry-After header waits exactly as asked (capped). Any
    other 4xx is a real bug in our request and is raised immediately.
    """
    delay = BACKOFF_BASE
    last_exc = None
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
            if response.status_code == 429 or response.status_code >= 500:
                if attempt < MAX_RETRIES - 1:
                    time.sleep(_retry_after_seconds(response, delay))
                    delay = min(delay * 2, MAX_BACKOFF)
                    continue
            response.raise_for_status()
            return response.json()
        except (requests.ConnectionError, requests.Timeout) as exc:
            last_exc = exc
            if attempt < MAX_RETRIES - 1:
                time.sleep(delay)
                delay = min(delay * 2, MAX_BACKOFF)
                continue
            raise
    # Retries exhausted on repeated 429/5xx responses.
    raise last_exc or requests.RequestException("Open-Meteo request failed after retries")


# ---------------------------------------------------------------------------
# National overview: one card per region
# ---------------------------------------------------------------------------

def get_overview():
    """Current weather + air quality for all 14 regions.

    Returns {"regions": [...], "demo": bool, "error": bool}.
    """
    if current_app.config["DEMO_DATA"]:
        return _demo_overview()
    return _cached("overview", _build_overview)


def _build_overview():
    lats = ",".join(str(r["lat"]) for r in REGIONS)
    lons = ",".join(str(r["lon"]) for r in REGIONS)
    try:
        weather = _get_json(WEATHER_API, {
            "latitude": lats, "longitude": lons,
            "current": "temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m",
            "timezone": "Asia/Tashkent",
        })
        air = _get_json(AIR_API, {
            "latitude": lats, "longitude": lons,
            "current": "pm2_5,pm10",
            "timezone": "Asia/Tashkent",
        })
    except requests.RequestException:
        return {"regions": [], "demo": False, "error": True}

    # With multiple coordinates both APIs return a list, one item per point.
    weather = weather if isinstance(weather, list) else [weather]
    air = air if isinstance(air, list) else [air]

    cards = []
    for region, w, a in zip(REGIONS, weather, air):
        w_cur, a_cur = w.get("current", {}), a.get("current", {})
        label, icon = describe_weather(w_cur.get("weather_code"))
        pm25 = a_cur.get("pm2_5")
        cards.append({
            **region,
            "temp": w_cur.get("temperature_2m"),
            "humidity": w_cur.get("relative_humidity_2m"),
            "wind": w_cur.get("wind_speed_10m"),
            "weather_label": label,
            "icon": icon,
            "pm25": pm25,
            "pm10": a_cur.get("pm10"),
            "aqi": pm25_to_aqi(pm25),
        })
    return {"regions": cards, "demo": False, "error": False}


# ---------------------------------------------------------------------------
# Region detail page
# ---------------------------------------------------------------------------

def get_region_detail(slug):
    """Detail data for one of the 14 top-level regions."""
    region = get_region(slug)
    return get_detail(region["lat"], region["lon"], cache_key=f"region:{slug}")


def get_detail(lat, lon, cache_key):
    """Current conditions, 48h chart data and a 7-day forecast for a point.

    Works for ANY coordinates. This is how district pages get
    hyper-localised data: Open-Meteo blends satellite and model grids,
    so no physical monitoring station is needed at the exact spot.
    """
    if current_app.config["DEMO_DATA"]:
        return _demo_region_detail(cache_key)
    return _cached(f"detail:{cache_key}", lambda: _build_detail(lat, lon))


def _build_detail(lat, lon):
    try:
        weather = _get_json(WEATHER_API, {
            "latitude": lat, "longitude": lon,
            "current": "temperature_2m,relative_humidity_2m,apparent_temperature,"
                       "weather_code,wind_speed_10m,wind_direction_10m,surface_pressure",
            "hourly": "temperature_2m",
            "daily": "temperature_2m_max,temperature_2m_min,weather_code,precipitation_probability_max",
            "forecast_days": 7,
            "timezone": "Asia/Tashkent",
        })
        air = _get_json(AIR_API, {
            "latitude": lat, "longitude": lon,
            "current": "pm2_5,pm10,nitrogen_dioxide,ozone,sulphur_dioxide,carbon_monoxide,us_aqi",
            "hourly": "pm2_5",
            "forecast_days": 4,
            "timezone": "Asia/Tashkent",
        })
    except requests.RequestException:
        return {"error": True, "demo": False}

    return _compose_detail(weather, air, demo=False)


def _build_region_details_batch():
    """Build detail payloads for all 14 regions in two batched requests.

    Open-Meteo accepts comma-separated coordinate lists and returns a JSON
    array with one full result (current + hourly + daily) per point, so the
    whole country's detail data costs two HTTP calls instead of 28.

    Returns a ``{slug: detail}`` dict, or None if the batch call fails (the
    caller then falls back to individual, spaced-out requests).
    """
    lats = ",".join(str(r["lat"]) for r in REGIONS)
    lons = ",".join(str(r["lon"]) for r in REGIONS)
    try:
        weather = _get_json(WEATHER_API, {
            "latitude": lats, "longitude": lons,
            "current": "temperature_2m,relative_humidity_2m,apparent_temperature,"
                       "weather_code,wind_speed_10m,wind_direction_10m,surface_pressure",
            "hourly": "temperature_2m",
            "daily": "temperature_2m_max,temperature_2m_min,weather_code,precipitation_probability_max",
            "forecast_days": 7,
            "timezone": "Asia/Tashkent",
        })
        air = _get_json(AIR_API, {
            "latitude": lats, "longitude": lons,
            "current": "pm2_5,pm10,nitrogen_dioxide,ozone,sulphur_dioxide,carbon_monoxide,us_aqi",
            "hourly": "pm2_5",
            "forecast_days": 4,
            "timezone": "Asia/Tashkent",
        })
    except requests.RequestException:
        return None

    weather = weather if isinstance(weather, list) else [weather]
    air = air if isinstance(air, list) else [air]
    if len(weather) != len(REGIONS) or len(air) != len(REGIONS):
        return None  # unexpected shape — let the caller fall back

    return {
        region["slug"]: _compose_detail(w, a, demo=False)
        for region, w, a in zip(REGIONS, weather, air)
    }


def _compose_detail(weather, air, demo):
    w_cur, a_cur = weather.get("current", {}), air.get("current", {})
    label, icon = describe_weather(w_cur.get("weather_code"))
    pm25 = a_cur.get("pm2_5")

    # 48-hour chart series (temperature + PM2.5 share the time axis).
    hours = weather.get("hourly", {}).get("time", [])[:48]
    temps = weather.get("hourly", {}).get("temperature_2m", [])[:48]
    pm25_series = air.get("hourly", {}).get("pm2_5", [])[:48]

    daily = weather.get("daily", {})
    days = []
    for i, date in enumerate(daily.get("time", [])[:7]):
        d_label, d_icon = describe_weather(daily["weather_code"][i])
        days.append({
            "date": date,
            "weekday": datetime.fromisoformat(date).strftime("%a"),
            "tmax": daily["temperature_2m_max"][i],
            "tmin": daily["temperature_2m_min"][i],
            "rain_prob": (daily.get("precipitation_probability_max") or [None] * 7)[i],
            "label": d_label,
            "icon": d_icon,
        })

    pollutants = [
        ("PM2.5", pm25, "ug/m3"),
        ("PM10", a_cur.get("pm10"), "ug/m3"),
        ("NO2", a_cur.get("nitrogen_dioxide"), "ug/m3"),
        ("O3", a_cur.get("ozone"), "ug/m3"),
        ("SO2", a_cur.get("sulphur_dioxide"), "ug/m3"),
        ("CO", a_cur.get("carbon_monoxide"), "ug/m3"),
    ]

    return {
        "error": False,
        "demo": demo,
        "current": {
            "temp": w_cur.get("temperature_2m"),
            "feels_like": w_cur.get("apparent_temperature"),
            "humidity": w_cur.get("relative_humidity_2m"),
            "wind": w_cur.get("wind_speed_10m"),
            "pressure": w_cur.get("surface_pressure"),
            "weather_label": label,
            "icon": icon,
        },
        "aqi": pm25_to_aqi(pm25),
        "pollutants": pollutants,
        "chart": {"times": hours, "temp": temps, "pm25": pm25_series},
        "daily": days,
    }


# ---------------------------------------------------------------------------
# Demo data (offline development only — always labelled in the UI)
# ---------------------------------------------------------------------------

def _demo_overview():
    cards = []
    for region in REGIONS:
        rng = random.Random(region["slug"])  # deterministic per region
        pm25 = round(rng.uniform(6, 70), 1)
        code = rng.choice([0, 1, 2, 3, 61])
        label, icon = describe_weather(code)
        cards.append({
            **region,
            "temp": round(rng.uniform(24, 39), 1),
            "humidity": rng.randint(20, 60),
            "wind": round(rng.uniform(4, 18), 1),
            "weather_label": label,
            "icon": icon,
            "pm25": pm25,
            "pm10": round(pm25 * 1.8, 1),
            "aqi": pm25_to_aqi(pm25),
        })
    return {"regions": cards, "demo": True, "error": False}


def _demo_region_detail(slug):
    rng = random.Random(slug)
    start = datetime.now().replace(minute=0, second=0, microsecond=0)
    hours = [(start + timedelta(hours=i)).isoformat(timespec="minutes") for i in range(48)]
    temps = [round(28 + 8 * rng.random(), 1) for _ in hours]
    pm25_series = [round(10 + 40 * rng.random(), 1) for _ in hours]
    pm25 = pm25_series[0]

    weather = {
        "current": {
            "temperature_2m": temps[0], "apparent_temperature": temps[0] + 1.5,
            "relative_humidity_2m": rng.randint(20, 60), "weather_code": 1,
            "wind_speed_10m": 11.0, "wind_direction_10m": 220, "surface_pressure": 1009.0,
        },
        "hourly": {"time": hours, "temperature_2m": temps},
        "daily": {
            "time": [(start + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7)],
            "temperature_2m_max": [round(30 + 8 * rng.random(), 1) for _ in range(7)],
            "temperature_2m_min": [round(18 + 6 * rng.random(), 1) for _ in range(7)],
            "weather_code": [rng.choice([0, 1, 2, 3, 61]) for _ in range(7)],
            "precipitation_probability_max": [rng.randint(0, 40) for _ in range(7)],
        },
    }
    air = {
        "current": {
            "pm2_5": pm25, "pm10": round(pm25 * 1.8, 1), "nitrogen_dioxide": 21.0,
            "ozone": 88.0, "sulphur_dioxide": 6.0, "carbon_monoxide": 240.0,
        },
        "hourly": {"time": hours, "pm2_5": pm25_series},
    }
    return _compose_detail(weather, air, demo=True)
