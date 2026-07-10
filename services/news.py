"""Environment news: a curated local library + optional live headlines.

Two independent sources, combined on the News page:

1. CURATED LIBRARY (always available, costs nothing): 100+ landmark
   environmental stories hand-picked into data/environmental_news.json.
   Every entry links to a stable, real page (Wikipedia / WHO) that has
   survived for years and opens in a new tab - so the News section is
   always full, professional and free, even with no API key configured.
   The display order is shuffled deterministically per day, so the page
   feels fresh every morning without any external call.

2. LIVE HEADLINES via Currents API (free tier), when CURRENTS_API_KEY
   is set. Chosen after checking NewsAPI.org, GNews and Currents API
   pricing and terms of service directly: NewsAPI's free tier cannot
   legally run in production at all, and GNews's free tier explicitly
   bans commercial use. Currents API's free tier (1,000 requests/day,
   no comparable commercial-use ban) is the one that's actually usable
   on a live site at no cost. Queries are strictly environment-scoped
   (see KEYWORDS_* below). Cached hourly like the weather data.
"""
import json
import random
from datetime import date
from pathlib import Path

import requests
from flask import current_app

from extensions import cache

API_URL = "https://api.currentsapi.services/v1/search"
REQUEST_TIMEOUT = 10
NEWS_CACHE_SECONDS = 3600  # refresh at most once an hour
STALE_CACHE_KEY = "news:aqi:stale"
CACHE_KEY = "news:aqi"

# Two tiers, queried in order: air-pollution-specific terms fill the
# page first; broader environment/climate terms only fill in whatever's
# left over. This is two Currents calls per refresh (still cached
# hourly - a couple of dozen calls a day, nowhere near the 1,000/day
# free-tier budget) instead of one, so the page is dominated by air
# pollution stories on days there are enough of them, and never empty
# on the (more common) days there aren't.
KEYWORDS_STRICT = "air pollution OR air quality OR smog OR PM2.5 OR particulate matter OR haze"
KEYWORDS_BROAD = "air quality OR climate change OR emissions OR environment OR wildfire smoke"
MAX_ARTICLES = 12

CURATED_PATH = Path(__file__).parent.parent / "data" / "environmental_news.json"
UZ_NEWS_PATH = Path(__file__).parent.parent / "data" / "uzbekistan_news.json"


def _api_key():
    return current_app.config.get("CURRENTS_API_KEY", "")


_curated_cache = None
_uz_news_cache = None


def get_uzbekistan():
    """Uzbekistan's 2025-2026 environmental plans and initiatives.

    A small curated file (data/uzbekistan_news.json) of this year's
    national stories - kept in chronological order (newest first), never
    shuffled, because "what is my country doing this year" reads as a
    timeline, not a grab-bag. Loaded once per process; a missing or
    corrupt file just means the section is hidden.
    """
    global _uz_news_cache
    if _uz_news_cache is None:
        try:
            data = json.loads(UZ_NEWS_PATH.read_text(encoding="utf-8"))
            _uz_news_cache = data.get("items") or []
        except Exception:
            _uz_news_cache = []
    return _uz_news_cache


def get_curated():
    """The local library of landmark environmental stories.

    Loaded from disk once per process, then re-ordered deterministically
    per calendar day (same shuffle for every visitor on a given day, a
    fresh one tomorrow). Never raises - a missing/corrupt file just
    means an empty list, and the page falls back to live headlines.
    """
    global _curated_cache
    if _curated_cache is None:
        try:
            data = json.loads(CURATED_PATH.read_text(encoding="utf-8"))
            _curated_cache = data.get("items") or []
        except Exception:
            _curated_cache = []
    if not _curated_cache:
        return []
    items = list(_curated_cache)
    random.Random(date.today().toordinal()).shuffle(items)
    return items


def get_news():
    """Curated library + cached recent live articles.

    Returns {"articles": [...live...], "curated": [...], "error": bool,
    "stale": bool, "configured": bool}. Never raises: a failed live
    fetch falls back to the last good list if one exists, otherwise an
    empty list - the curated library keeps the page full either way,
    and headlines are never fabricated.
    """
    local = {"curated": get_curated(), "uzbekistan": get_uzbekistan()}
    if not _api_key():
        return {"articles": [], "error": False, "stale": False,
                "configured": False, **local}

    cached = cache.get(CACHE_KEY)
    if cached is not None:
        return {**cached, **local}

    try:
        articles = _fetch()
        result = {"articles": articles, "error": False, "stale": False, "configured": True}
        cache.set(CACHE_KEY, result, timeout=NEWS_CACHE_SECONDS)
        cache.set(STALE_CACHE_KEY, result, timeout=0)
        return {**result, **local}
    except Exception:
        # Broad on purpose: news is a nice-to-have, never worth a 500.
        # Anything from a network blip to an unexpected response shape
        # just falls back to the last good list (or an empty state).
        stale = cache.get(STALE_CACHE_KEY)
        if stale is not None:
            stale = dict(stale)
            stale["stale"] = True
            cache.set(CACHE_KEY, stale, timeout=300)
            return {**stale, **local}
        empty = {"articles": [], "error": True, "stale": False, "configured": True}
        cache.set(CACHE_KEY, empty, timeout=120)
        return {**empty, **local}


def _fetch():
    articles = _search(KEYWORDS_STRICT)
    seen = {a["url"] for a in articles}
    if len(articles) < MAX_ARTICLES:
        for a in _search(KEYWORDS_BROAD):
            if a["url"] in seen:
                continue
            articles.append(a)
            seen.add(a["url"])
            if len(articles) >= MAX_ARTICLES:
                break
    return articles[:MAX_ARTICLES]


def _search(keywords):
    response = requests.get(
        API_URL, timeout=REQUEST_TIMEOUT,
        headers={"Authorization": _api_key()},
        params={"keywords": keywords, "language": "en"},
    )
    response.raise_for_status()
    data = response.json()
    if data.get("status") != "ok":
        return []

    articles = []
    for item in (data.get("news") or [])[:MAX_ARTICLES]:
        parsed = _parse_article(item)
        if parsed:
            articles.append(parsed)
    return articles


def _parse_article(item):
    # Currents' own docs disagree with themselves on this field's shape
    # ("url" string in examples, "urls" string|list in the formal
    # schema) - handle whichever shows up.
    url = item.get("url")
    if not url:
        urls_field = item.get("urls")
        if isinstance(urls_field, list) and urls_field:
            url = urls_field[0]
        elif isinstance(urls_field, str):
            url = urls_field
    title = item.get("title")
    if not url or not title:
        return None
    image = item.get("image")
    if image in (None, "None", ""):
        image = None
    return {
        "title": title,
        "description": _trim(item.get("description")),
        "url": url,
        "image": image,
        "author": item.get("author") if item.get("author") not in (None, "None") else None,
        "published": _format_date(item.get("published")),
    }


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
