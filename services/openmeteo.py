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
from datetime import datetime, timedelta

import requests
from flask import current_app

from extensions import cache
from services.aqi import pm25_to_aqi
from services.regions import REGIONS, get_region

WEATHER_API = "https://api.open-meteo.com/v1/forecast"
AIR_API = "https://air-quality-api.open-meteo.com/v1/air-quality"
REQUEST_TIMEOUT = 15

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
    """Return the cached value for *key*, rebuilding it when expired.

    Successful payloads live for CACHE_TTL_SECONDS (the background job
    refreshes them long before they expire). Error payloads are only
    cached for 60 seconds so a temporary API hiccup heals quickly.
    """
    value = cache.get(key)
    if value is not None:
        return value
    value = builder()
    timeout = 60 if value.get("error") else current_app.config["CACHE_TTL_SECONDS"]
    cache.set(key, value, timeout=timeout)
    return value


def warm_cache():
    """Prefetch the national overview and all 14 region pages.

    Runs in a background thread on a schedule, so every user request is
    served instantly from memory instead of waiting on external APIs.
    """
    ttl = current_app.config["CACHE_TTL_SECONDS"]

    overview = _build_overview()
    if not overview.get("error"):
        cache.set("overview", overview, timeout=ttl)

    for region in REGIONS:
        detail = _build_detail(region["lat"], region["lon"])
        if not detail.get("error"):
            cache.set(f"detail:region:{region['slug']}", detail, timeout=ttl)


def _get_json(url, params):
    response = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    return response.json()


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
