"""Failure-scenario tests for the Open-Meteo resilience layer.

Run with:  venv/Scripts/python.exe test_resilience.py

These simulate exactly what happens on Render's free tier:
  1. A rate-limited (429) call that succeeds on retry.
  2. A refresh that fails outright but has a prior snapshot -> stale, no error.
  3. A page that has never loaded and fails -> honest error.
  4. A server restart (memory wiped) restoring real data from Supabase.
  5. Batched warm-up costs 2 calls for all 14 regions, not 28.
  6. Normal happy-path regression.
"""
import os
import sys

os.environ["DEMO_DATA"] = "0"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["TESTING"] = "1"

import requests

from app import create_app
from config import Config
from extensions import cache, db
from services import openmeteo, snapshots
from services.regions import REGIONS


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    CACHE_TYPE = "SimpleCache"


app = create_app(TestConfig)
PASS, FAIL = 0, 0


def check(name, condition):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  PASS  {name}")
    else:
        FAIL += 1
        print(f"  FAIL  {name}")


# --- fake HTTP layer --------------------------------------------------------

class FakeResp:
    def __init__(self, status=200, body=None, headers=None):
        self.status_code = status
        self._body = body if body is not None else {}
        self.headers = headers or {}

    def json(self):
        return self._body

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}", response=self)


def weather_body():
    return {"current": {"temperature_2m": 30, "relative_humidity_2m": 40,
                        "apparent_temperature": 31, "weather_code": 1,
                        "wind_speed_10m": 10, "wind_direction_10m": 200,
                        "surface_pressure": 1010},
            "hourly": {"time": ["2026-07-05T00:00"], "temperature_2m": [30]},
            "daily": {"time": ["2026-07-05"], "temperature_2m_max": [35],
                      "temperature_2m_min": [22], "weather_code": [1],
                      "precipitation_probability_max": [10]}}


def air_body():
    return {"current": {"pm2_5": 20, "pm10": 35, "nitrogen_dioxide": 21,
                        "ozone": 88, "sulphur_dioxide": 6, "carbon_monoxide": 240},
            "hourly": {"time": ["2026-07-05T00:00"], "pm2_5": [20]}}


with app.app_context():
    # -----------------------------------------------------------------
    print("\n[1] 429 rate limit, then success on retry")
    calls = {"n": 0}

    def flaky_get(url, params=None, timeout=None):
        calls["n"] += 1
        if calls["n"] == 1:
            return FakeResp(429, headers={"Retry-After": "0"})
        return FakeResp(200, weather_body())

    openmeteo.requests.get = flaky_get
    out = openmeteo._get_json(openmeteo.WEATHER_API, {})
    check("retried past the 429 and returned data", out.get("current", {}).get("temperature_2m") == 30)
    check("made exactly 2 attempts", calls["n"] == 2)

    # -----------------------------------------------------------------
    print("\n[2] refresh fails but a snapshot exists -> stale, never error")
    cache.clear()
    good = {"error": False, "regions": [{"name": "X", "pm25": 12}], "demo": False}
    snapshots.save("overview", good)

    def always_500(url, params=None, timeout=None):
        return FakeResp(500)

    openmeteo.requests.get = always_500
    result = openmeteo.get_overview()
    check("no red error shown", result.get("error") is False)
    check("marked stale", result.get("stale") is True)
    check("served the real prior data", result["regions"][0]["pm25"] == 12)

    # -----------------------------------------------------------------
    print("\n[3] never-loaded page that fails -> honest error banner")
    cache.clear()
    openmeteo.requests.get = always_500
    result = openmeteo.get_detail(41.0, 69.0, cache_key="loc:99999")
    check("error surfaces only when no snapshot ever existed", result.get("error") is True)

    # -----------------------------------------------------------------
    print("\n[4] server restart: memory wiped, data restored from DB snapshot")
    cache.clear()  # simulate a fresh worker with empty SimpleCache
    openmeteo.requests.get = always_500  # API still down during the cold start
    result = openmeteo.get_overview()
    check("cold start still serves real data from Supabase snapshot", result["regions"][0]["pm25"] == 12)
    check("and shows it as stale, not broken", result.get("stale") is True and not result.get("error"))

    # -----------------------------------------------------------------
    print("\n[5] batched warm-up: all 14 regions in 2 calls")
    cache.clear()
    calls["n"] = 0

    def counting_get(url, params=None, timeout=None):
        calls["n"] += 1
        body = [weather_body() for _ in REGIONS] if "air-quality" not in url \
            else [air_body() for _ in REGIONS]
        return FakeResp(200, body)

    openmeteo.requests.get = counting_get
    details = openmeteo._build_region_details_batch()
    check("built all 14 region details", details is not None and len(details) == len(REGIONS))
    check("cost exactly 2 HTTP calls (not 28)", calls["n"] == 2)
    check("each detail is well-formed", details["andijan"]["current"]["temp"] == 30)

    # -----------------------------------------------------------------
    print("\n[6] happy-path regression: fresh good data is cached + snapshotted")
    cache.clear()

    def good_single(url, params=None, timeout=None):
        return FakeResp(200, weather_body() if "air-quality" not in url else air_body())

    openmeteo.requests.get = good_single
    result = openmeteo.get_detail(41.3, 69.2, cache_key="loc:123")
    check("returns live data with no error/stale flags", result.get("error") is False and not result.get("stale"))
    check("current temperature parsed", result["current"]["temp"] == 30)
    check("snapshot persisted for next cold start", snapshots.load("detail:loc:123") is not None)

print(f"\n{'='*48}\n  {PASS} passed, {FAIL} failed\n{'='*48}")
sys.exit(1 if FAIL else 0)
