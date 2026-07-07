"""Environment / air-quality news via Currents API (free tier).

Chosen after checking NewsAPI.org, GNews and Currents API pricing and
terms of service directly: NewsAPI's free tier cannot legally run in
production at all, and GNews's free tier explicitly bans commercial
use. Currents API's free tier (1,000 requests/day, no comparable
commercial-use ban) is the one that's actually usable on a live site
at no cost.

Cached like the weather data (see services/openmeteo.py's _cached
helper) so page views never wait on - or multiply - the external call:
refreshed at most once an hour, which is a tiny fraction of the daily
budget no matter how much traffic the News page gets.
"""
import requests
from flask import current_app

from extensions import cache

API_URL = "https://api.currentsapi.services/v1/search"
REQUEST_TIMEOUT = 10
NEWS_CACHE_SECONDS = 3600  # refresh at most once an hour
STALE_CACHE_KEY = "news:aqi:stale"
CACHE_KEY = "news:aqi"

# Kept broad on purpose: Currents has thin dedicated coverage of
# Uzbekistan specifically, so a narrow query would return almost
# nothing most days. Global air-quality/pollution coverage is still
# directly relevant to an air-quality app.
KEYWORDS = "air quality OR air pollution OR smog"
MAX_ARTICLES = 12


def _api_key():
    return current_app.config.get("CURRENTS_API_KEY", "")


def get_news():
    """Cached recent air-quality / environment articles.

    Returns {"articles": [...], "error": bool, "stale": bool,
    "configured": bool}. Never raises: a failed fetch falls back to the
    last good list if one exists, otherwise an empty, clearly-labelled
    result - never fabricated headlines.
    """
    if not _api_key():
        return {"articles": [], "error": False, "stale": False, "configured": False}

    cached = cache.get(CACHE_KEY)
    if cached is not None:
        return cached

    try:
        articles = _fetch()
        result = {"articles": articles, "error": False, "stale": False, "configured": True}
        cache.set(CACHE_KEY, result, timeout=NEWS_CACHE_SECONDS)
        cache.set(STALE_CACHE_KEY, result, timeout=0)
        return result
    except Exception:
        # Broad on purpose: news is a nice-to-have, never worth a 500.
        # Anything from a network blip to an unexpected response shape
        # just falls back to the last good list (or an empty state).
        stale = cache.get(STALE_CACHE_KEY)
        if stale is not None:
            stale = dict(stale)
            stale["stale"] = True
            cache.set(CACHE_KEY, stale, timeout=300)
            return stale
        empty = {"articles": [], "error": True, "stale": False, "configured": True}
        cache.set(CACHE_KEY, empty, timeout=120)
        return empty


def _fetch():
    response = requests.get(
        API_URL, timeout=REQUEST_TIMEOUT,
        headers={"Authorization": _api_key()},
        params={"keywords": KEYWORDS, "language": "en"},
    )
    response.raise_for_status()
    data = response.json()
    if data.get("status") != "ok":
        return []

    articles = []
    for item in (data.get("news") or [])[:MAX_ARTICLES]:
        # Currents' own docs disagree with themselves on this field's
        # shape ("url" string in examples, "urls" string|list in the
        # formal schema) - handle whichever shows up.
        url = item.get("url")
        if not url:
            urls_field = item.get("urls")
            if isinstance(urls_field, list) and urls_field:
                url = urls_field[0]
            elif isinstance(urls_field, str):
                url = urls_field
        title = item.get("title")
        if not url or not title:
            continue
        image = item.get("image")
        if image in (None, "None", ""):
            image = None
        articles.append({
            "title": title,
            "description": _trim(item.get("description")),
            "url": url,
            "image": image,
            "author": item.get("author") if item.get("author") not in (None, "None") else None,
            "published": _format_date(item.get("published")),
        })
    return articles


def _trim(text, limit=220):
    if not text:
        return ""
    text = text.strip()
    return text if len(text) <= limit else text[:limit].rsplit(" ", 1)[0] + "..."


def _format_date(raw):
    if not raw:
        return ""
    from datetime import datetime
    for fmt in ("%Y-%m-%d %H:%M:%S %z", "%Y-%m-%dT%H:%M:%S%z"):
        try:
            return datetime.strptime(raw, fmt).strftime("%d %b %Y")
        except ValueError:
            continue
    return raw[:10]
