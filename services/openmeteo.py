"""Weather + air-quality client (WeatherAPI.com).

One authenticated call to WeatherAPI returns current weather, a 3-day
forecast (hourly) AND air-quality in a single response, so we no longer
depend on Open-Meteo's shared-IP daily limit. The output dict shape is
unchanged, so templates and the rest of the app are untouched.

Set WEATHERAPI_KEY in the environment (Render -> Environment). If it is
missing the app clearly reports it on the /admin/diagnostics page.
"""
import json
import random
import time
from datetime import datetime, timedelta, timezone

import requests
from flask import current_app

from extensions import cache
from services.aqi import pm25_to_aqi
from services.regions import REGIONS, get_region

API_URL = "https://api.weatherapi.com/v1/forecast.json"
# Trimmed from 15s/3 retries: real-time data is always preferred, but if
# WeatherAPI is struggling we want to fall back to the last-good preview
# (see _load_stale below) quickly rather than making a request wait up to
# ~90s worst case. Two attempts still absorb a single transient blip.
REQUEST_TIMEOUT = 10
HEADERS = {"User-Agent": "EcoPulse/1.0 (+https://github.com/jalencik/ECO-PULSY)"}
MAX_RETRIES = 2
STAGGER_SECONDS = 0.4  # tiny pause between the 14 overview calls

# WeatherAPI condition codes -> (human label, icon id in the SVG sprite).
_RAIN = {1063, 1069, 1072, 1150, 1153, 1168, 1171, 1180, 1183, 1186, 1189,
         1192, 1195, 1198, 1201, 1240, 1243, 1246, 1249, 1252}
_SNOW = {1066, 1114, 1117, 1210, 1213, 1216, 1219, 1222, 1225, 1237,
         1255, 1258, 1261, 1264}
_STORM = {1087, 1273, 1276, 1279, 1282}
_FOG = {1030, 1135, 1147}


def _uv_label(uv):
    """Standard WHO UV Index category. None when uv itself is unknown."""
    if uv is None:
        return None
    if uv < 3:
        return "Low"
    if uv < 6:
        return "Moderate"
    if uv < 8:
        return "High"
    if uv < 11:
        return "Very High"
    return "Extreme"


def describe_weather(code):
    if code is None:
        return ("Unknown", "cloud")
    if code == 1000:
        return ("Clear", "sun")
    if code == 1003:
        return ("Partly cloudy", "sun-cloud")
    if code in (1006, 1009):
        return ("Cloudy", "cloud")
    if code in _FOG:
        return ("Fog", "fog")
    if code in _STORM:
        return ("Thunderstorm", "storm")
    if code in _SNOW:
        return ("Snow", "snow")
    if code in _RAIN:
        return ("Rain", "rain")
    return ("Cloudy", "cloud")


def _api_key():
    return current_app.config.get("WEATHERAPI_KEY", "")


# ---------------------------------------------------------------------------
# Resilient HTTP
# ---------------------------------------------------------------------------

def _get_json(params):
    """GET WeatherAPI with retries and clear logging of any failure."""
    last_error = None
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.get(API_URL, params=params,
                                    timeout=REQUEST_TIMEOUT, headers=HEADERS)
            if response.status_code == 429:
                wait = response.headers.get("Retry-After")
                wait = int(wait) if wait and wait.isdigit() else 2 ** attempt * 2
                time.sleep(min(wait, 20))
                last_error = requests.RequestException("rate limited (429)")
                continue
            response.raise_for_status()
            return response.json()
        except requests.RequestException as exc:
            last_error = exc
            current_app.logger.warning(
                "WeatherAPI attempt %s/%s failed: %s", attempt + 1, MAX_RETRIES, exc
            )
            if attempt < MAX_RETRIES - 1:
                time.sleep(2 ** attempt * 2)
    raise last_error


def _fetch(lat, lon, days=3):
    """Raw WeatherAPI payload for a point (weather + forecast + AQI)."""
    return _get_json({
        "key": _api_key(), "q": f"{lat},{lon}",
        "days": days, "aqi": "yes",
    })


# ---------------------------------------------------------------------------
# Cache layer with stale-while-revalidate + DB snapshot persistence
# ---------------------------------------------------------------------------

def _cached(key, builder):
    value = cache.get(key)
    if value is not None:
        return value
    value = builder()
    if not value.get("error"):
        _store(key, value)
        return value
    stale = _load_stale(key)
    if stale is not None:
        stale = dict(stale)
        stale["stale"] = True
        # "Real-time first, honest preview if it can't be helped": tell
        # the user how old the preview is rather than just "delayed".
        stale["updated_minutes_ago"] = _minutes_ago(stale.get("updated_at"))
        cache.set(key, stale, timeout=300)
        return stale
    cache.set(key, value, timeout=60)
    return value


def _minutes_ago(iso_timestamp):
    if not iso_timestamp:
        return None
    try:
        then = datetime.fromisoformat(iso_timestamp)
    except ValueError:
        return None
    return max(0, int((datetime.now(timezone.utc) - then).total_seconds() // 60))


def _store(key, value):
    value["updated_at"] = datetime.now(timezone.utc).isoformat()
    cache.set(key, value, timeout=current_app.config["CACHE_TTL_SECONDS"])
    cache.set(f"stale:{key}", value, timeout=0)
    try:
        from extensions import db
        from models import Snapshot

        snap = db.session.get(Snapshot, key) or Snapshot(key=key)
        snap.payload = value
        db.session.add(snap)
        db.session.commit()
    except Exception:
        try:
            from extensions import db
            db.session.rollback()
        except Exception:
            pass


def _load_stale(key):
    value = cache.get(f"stale:{key}")
    if value is not None:
        return value
    try:
        from models import Snapshot
        from extensions import db

        snap = db.session.get(Snapshot, key)
        if snap is not None:
            value = snap.payload
            if isinstance(value, str):
                value = json.loads(value)
            cache.set(f"stale:{key}", value, timeout=0)
            return value
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# Background prefetch: one loop warms BOTH the overview and every region page
# ---------------------------------------------------------------------------

def warm_cache():
    if not _api_key():
        return
    _refresh_all(store_details=True)


def _refresh_all(store_details):
    """Fetch all 14 regions once; return the overview and (optionally)
    cache each region's detail page from the same responses."""
    cards = []
    for region in REGIONS:
        try:
            payload = _fetch(region["lat"], region["lon"])
        except requests.RequestException:
            continue
        cards.append(_overview_card(region, payload))
        if store_details:
            _store(f"detail:region:{region['slug']}", _compose_detail(payload))
        time.sleep(STAGGER_SECONDS)

    if not cards:
        return {"regions": [], "demo": False, "error": True}
    overview = {"regions": cards, "demo": False, "error": False}
    return overview


# ---------------------------------------------------------------------------
# National overview
# ---------------------------------------------------------------------------

def get_overview():
    if current_app.config["DEMO_DATA"]:
        return _demo_overview()
    if not _api_key():
        return {"regions": [], "demo": False, "error": True}
    return _cached("overview", lambda: _refresh_all(store_details=True))


def _overview_card(region, payload):
    cur = payload.get("current", {})
    cond = cur.get("condition", {})
    label, icon = describe_weather(cond.get("code"))
    aq = cur.get("air_quality", {})
    pm25 = aq.get("pm2_5")
    return {
        **region,
        "temp": cur.get("temp_c"),
        "humidity": cur.get("humidity"),
        "wind": cur.get("wind_kph"),
        "weather_label": label,
        "icon": icon,
        "pm25": round(pm25, 1) if pm25 is not None else None,
        "pm10": round(aq["pm10"], 1) if aq.get("pm10") is not None else None,
        "aqi": pm25_to_aqi(pm25),
    }


# ---------------------------------------------------------------------------
# Region / district detail
# ---------------------------------------------------------------------------

def get_region_detail(slug):
    region = get_region(slug)
    return get_detail(region["lat"], region["lon"], cache_key=f"region:{slug}")


def get_detail(lat, lon, cache_key):
    if current_app.config["DEMO_DATA"]:
        return _demo_region_detail(cache_key)
    if not _api_key():
        return {"error": True, "demo": False}
    return _cached(f"detail:{cache_key}", lambda: _build_detail(lat, lon))


def _build_detail(lat, lon):
    try:
        payload = _fetch(lat, lon)
    except requests.RequestException:
        return {"error": True, "demo": False}
    return _compose_detail(payload)


def _compose_detail(payload):
    cur = payload.get("current", {})
    cond = cur.get("condition", {})
    label, icon = describe_weather(cond.get("code"))
    aq = cur.get("air_quality", {})
    pm25 = aq.get("pm2_5")

    # Flatten hourly forecast into a 48-hour series for the trend chart,
    # and keep each day's full real hourly breakdown too (24 real
    # WeatherAPI hours per day, for the expandable hourly forecast view -
    # nothing here is interpolated or invented).
    hours, temps, pm_series = [], [], []
    days = []
    forecastdays = payload.get("forecast", {}).get("forecastday", [])
    for day in forecastdays:
        d = day.get("day", {})
        d_label, d_icon = describe_weather(d.get("condition", {}).get("code"))

        day_hours = []
        day_pm_values = []
        for h in day.get("hour", []):
            hp = h.get("air_quality", {}).get("pm2_5")
            hours.append(h.get("time"))
            temps.append(h.get("temp_c"))
            pm_series.append(round(hp, 1) if hp is not None else None)
            if hp is not None:
                day_pm_values.append(hp)

            h_label, h_icon = describe_weather(h.get("condition", {}).get("code"))
            time_str = h.get("time") or ""
            day_hours.append({
                "hour_label": time_str[-5:] if len(time_str) >= 5 else time_str,
                "temp": h.get("temp_c"),
                "label": h_label,
                "icon": h_icon,
                "pm25": round(hp, 1) if hp is not None else None,
                "aqi": pm25_to_aqi(hp),
                "rain_prob": h.get("chance_of_rain"),
                "wind": h.get("wind_kph"),
                "wind_degree": h.get("wind_degree"),
                "wind_dir": h.get("wind_dir"),
            })

        # A day-level AQI so the collapsed forecast row can show one too
        # (matches the reference layout) without inventing anything: it's
        # a plain average of that SAME day's real hourly PM2.5 readings
        # above, the same kind of honest averaging views._summarise()
        # already does for the national dashboard summary.
        day_pm25 = round(sum(day_pm_values) / len(day_pm_values), 1) if day_pm_values else None

        days.append({
            "date": day.get("date"),
            "weekday": datetime.fromisoformat(day["date"]).strftime("%a"),
            "tmax": d.get("maxtemp_c"),
            "tmin": d.get("mintemp_c"),
            "rain_prob": d.get("daily_chance_of_rain"),
            "wind": d.get("maxwind_kph"),
            "label": d_label,
            "icon": d_icon,
            "aqi": pm25_to_aqi(day_pm25),
            "hours": day_hours,
        })
    hours, temps, pm_series = hours[:48], temps[:48], pm_series[:48]

    pollutants = [
        ("PM2.5", round(pm25, 1) if pm25 is not None else None, "ug/m3"),
        ("PM10", _r(aq.get("pm10")), "ug/m3"),
        ("NO2", _r(aq.get("no2")), "ug/m3"),
        ("O3", _r(aq.get("o3")), "ug/m3"),
        ("SO2", _r(aq.get("so2")), "ug/m3"),
        ("CO", _r(aq.get("co")), "ug/m3"),
    ]

    # Today's sunrise/sunset/UV - all straight from WeatherAPI's own
    # astro block for day 0 (today), never computed or estimated locally.
    today_astro = forecastdays[0].get("astro", {}) if forecastdays else {}

    return {
        "error": False, "demo": False,
        "current": {
            "temp": cur.get("temp_c"),
            "feels_like": cur.get("feelslike_c"),
            "humidity": cur.get("humidity"),
            "wind": cur.get("wind_kph"),
            "pressure": cur.get("pressure_mb"),
            "weather_label": label,
            "icon": icon,
            "uv": cur.get("uv"),
            "uv_label": _uv_label(cur.get("uv")),
            "sunrise": today_astro.get("sunrise"),
            "sunset": today_astro.get("sunset"),
        },
        "aqi": pm25_to_aqi(pm25),
        "pollutants": pollutants,
        "chart": {"times": hours, "temp": temps, "pm25": pm_series},
        "daily": days,
    }


def _r(v):
    return round(v, 1) if v is not None else None


# ---------------------------------------------------------------------------
# Demo data (offline dev only — always labelled in the UI)
# ---------------------------------------------------------------------------

def _demo_overview():
    cards = []
    for region in REGIONS:
        rng = random.Random(region["slug"])
        pm25 = round(rng.uniform(6, 70), 1)
        label, icon = describe_weather(rng.choice([1000, 1003, 1006, 1063]))
        cards.append({
            **region, "temp": round(rng.uniform(24, 39), 1),
            "humidity": rng.randint(20, 60), "wind": round(rng.uniform(4, 18), 1),
            "weather_label": label, "icon": icon, "pm25": pm25,
            "pm10": round(pm25 * 1.8, 1), "aqi": pm25_to_aqi(pm25),
        })
    return {"regions": cards, "demo": True, "error": False}


def _demo_region_detail(slug):
    rng = random.Random(slug)
    start = datetime.now().replace(minute=0, second=0, microsecond=0)
    hours = [(start + timedelta(hours=i)).isoformat(timespec="minutes") for i in range(48)]
    temps = [round(28 + 8 * rng.random(), 1) for _ in hours]
    pm_series = [round(10 + 40 * rng.random(), 1) for _ in hours]
    pm25 = pm_series[0]
    demo_uv = round(rng.uniform(1, 9), 1)
    days = [{
        "date": (start + timedelta(days=i)).strftime("%Y-%m-%d"),
        "weekday": (start + timedelta(days=i)).strftime("%a"),
        "tmax": round(30 + 8 * rng.random(), 1), "tmin": round(18 + 6 * rng.random(), 1),
        "rain_prob": rng.randint(0, 40),
        "wind": round(rng.uniform(8, 22), 1),
        "label": "Clear", "icon": "sun",
        "aqi": pm25_to_aqi(round(10 + 40 * rng.random(), 1)),
        "hours": [{
            "hour_label": f"{h:02d}:00",
            "temp": round(20 + 12 * rng.random(), 1),
            "label": "Clear", "icon": "sun",
            "pm25": round(10 + 40 * rng.random(), 1),
            "aqi": pm25_to_aqi(round(10 + 40 * rng.random(), 1)),
            "rain_prob": rng.randint(0, 30),
            "wind": round(rng.uniform(4, 20), 1),
            "wind_degree": rng.randint(0, 359),
            "wind_dir": rng.choice(["N", "NE", "E", "SE", "S", "SW", "W", "NW"]),
        } for h in range(24)],
    } for i in range(3)]
    return {
        "error": False, "demo": True,
        "current": {"temp": temps[0], "feels_like": temps[0] + 1.5,
                    "humidity": rng.randint(20, 60), "wind": 11.0,
                    "pressure": 1009.0, "weather_label": "Clear", "icon": "sun",
                    "uv": demo_uv, "uv_label": _uv_label(demo_uv),
                    "sunrise": "05:52 AM", "sunset": "07:41 PM"},
        "aqi": pm25_to_aqi(pm25),
        "pollutants": [("PM2.5", pm25, "ug/m3"), ("PM10", round(pm25 * 1.8, 1), "ug/m3"),
                       ("NO2", 21.0, "ug/m3"), ("O3", 88.0, "ug/m3"),
                       ("SO2", 6.0, "ug/m3"), ("CO", 240.0, "ug/m3")],
        "chart": {"times": hours, "temp": temps, "pm25": pm_series},
        "daily": days,
    }
