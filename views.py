"""Public pages, the dashboard, region and district pages, and the
small JSON API that powers the cascading location picker."""
import json
import math
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from flask import (Blueprint, abort, current_app, flash, g, jsonify,
                   redirect, render_template, request, url_for)
from flask_login import current_user, login_required

from extensions import db
from models import Location, TreePledge
from services import hurricanes as hurricanes_service
from services import news as news_service
from services import openmeteo
from services import storms as storms_service
from services import wildfires as wildfires_service
from services.regions import (REGIONS, dataset_key_for_slug, get_region,
                              region_display_name, slug_for_dataset_key)
from translations import DEFAULT_LANG, SUPPORTED_LANGS

views_bp = Blueprint("views", __name__)


@views_bp.route("/")
def index():
    """Landing page (logged-in users go straight to their dashboard)."""
    if current_user.is_authenticated:
        return redirect(url_for("views.dashboard"))

    # Trust badge below the hero CTA. Rounded DOWN to the nearest 50 so it
    # always reads as a clean, honest number and never overstates the
    # live count as it grows. Never blocks the landing page from loading.
    from models import User
    try:
        trust_count = (User.query.count() // 50) * 50
    except Exception:
        trust_count = 0

    return render_template("index.html", trust_count=trust_count)


@views_bp.route("/set-language/<lang>")
def set_language(lang):
    """Switch the site's display language (English / Uzbek).

    Stored as a plain cookie - no account change, and works for
    logged-out visitors on the landing page too. Redirects back to
    wherever the switcher was clicked from; any "next" value that isn't
    a local path is ignored (open-redirect guard) in favour of the
    homepage.
    """
    if lang not in SUPPORTED_LANGS:
        lang = DEFAULT_LANG
    target = request.args.get("next") or ""
    if not target.startswith("/") or target.startswith("//"):
        target = url_for("views.index")
    response = redirect(target)
    response.set_cookie("lang", lang, max_age=60 * 60 * 24 * 365, samesite="Lax")
    return response


@views_bp.route("/dashboard")
@login_required
def dashboard():
    overview = openmeteo.get_overview()
    return render_template(
        "dashboard.html", overview=overview, summary=_summarise(overview)
    )


def _summarise(overview):
    """National headline numbers derived from the region cards."""
    regions = [r for r in overview["regions"] if r.get("pm25") is not None]
    if not regions:
        return None
    return {
        "avg_pm25": round(sum(r["pm25"] for r in regions) / len(regions), 1),
        "cleanest": min(regions, key=lambda r: r["pm25"]),
        "worst": max(regions, key=lambda r: r["pm25"]),
    }


@views_bp.route("/regions/<slug>")
@login_required
def region(slug):
    reg = get_region(slug)
    if reg is None:
        abort(404)
    data = openmeteo.get_region_detail(slug)
    return render_template("region.html", region=reg, data=data)


@views_bp.route("/locations/<int:location_id>")
@login_required
def location(location_id):
    """District detail page: coordinate-precise data with a safe fallback."""
    loc = db.session.get(Location, location_id)
    if loc is None:
        abort(404)

    data = openmeteo.get_detail(loc.latitude, loc.longitude, cache_key=f"loc:{loc.id}")

    # Graceful degradation: if the exact point fails, fall back to the
    # regional administrative centre instead of showing an empty page.
    fallback = False
    region_slug = slug_for_dataset_key(loc.region_name)
    reg = get_region(region_slug) if region_slug else None
    if data.get("error") and reg is not None:
        data = openmeteo.get_region_detail(region_slug)
        fallback = not data.get("error")

    return render_template(
        "location.html",
        loc=loc, region=reg, data=data,
        fallback=fallback, active_slug=region_slug,
    )


@views_bp.route("/rankings")
@login_required
def rankings():
    """Hottest / most polluted / most humid / windiest, all 14 regions.

    Built entirely from the overview cache the dashboard already uses -
    no extra WeatherAPI calls. Expanding a region to rank its districts
    is a separate, lazy JSON call (see api_ranking_districts below).
    """
    overview = openmeteo.get_overview()
    return render_template(
        "rankings.html", overview=overview,
        rankings=_rank_regions(overview.get("regions", [])),
    )


def _rank_regions(regions):
    def ranked(metric_fn):
        usable = [r for r in regions if metric_fn(r) is not None]
        return sorted(usable, key=metric_fn, reverse=True)

    return {
        "hottest": ranked(lambda r: r.get("temp")),
        "polluted": ranked(lambda r: (r.get("aqi") or {}).get("value")),
        "humid": ranked(lambda r: r.get("humidity")),
        "windy": ranked(lambda r: r.get("wind")),
    }


@views_bp.route("/api/rankings/<slug>/districts")
@login_required
def api_ranking_districts(slug):
    """Lazy, cached per-district numbers for one region's Rankings expand.

    Only fetches the districts of the ONE region a visitor actually
    expands - never all 173 up front - so this stays well inside the
    WeatherAPI free-tier budget. Every district goes through get_detail's
    existing stale-while-revalidate cache under the SAME cache_key the
    district's own page uses (loc:<id>), so a district that's already
    been visited is free, and repeat expands by anyone are free for as
    long as that cache entry stays fresh. Real data only - a district
    that can't be fetched is marked "error" rather than guessed at.

    A region's districts are fetched CONCURRENTLY (thread pool), not one
    at a time. Flask is synchronous, so a region with a dozen+ districts
    all still cold would previously mean a dozen+ sequential WeatherAPI
    round-trips - easily 10-20+ seconds, which is what made this feel
    "stuck" rather than slow. Each district is independent I/O (its own
    cache key, its own HTTP call), so a small worker pool cuts that down
    to roughly one round-trip's worth of wall-clock time regardless of
    how many districts the region has.
    """
    reg = get_region(slug)
    dataset_key = dataset_key_for_slug(slug)
    if reg is None or dataset_key is None:
        abort(404)

    locations = (Location.query.filter_by(region_name=dataset_key)
                 .order_by(Location.district_name).all())

    def fetch_one(loc, app=current_app._get_current_object()):
        # Each worker thread needs its own push of the Flask app context -
        # current_app/db.session are context-local and don't cross thread
        # boundaries on their own. Same pattern the background prefetch
        # scheduler already uses (see services.openmeteo.warm_cache).
        with app.app_context():
            data = openmeteo.get_detail(loc.latitude, loc.longitude, cache_key=f"loc:{loc.id}")
        if data.get("error"):
            return {"id": loc.id, "name": loc.district_name, "error": True}
        cur = data.get("current", {})
        return {
            "id": loc.id,
            "name": loc.district_name,
            "error": False,
            "stale": bool(data.get("stale")),
            "temp": cur.get("temp"),
            "humidity": cur.get("humidity"),
            "wind": cur.get("wind"),
            "aqi": data.get("aqi"),
        }

    if locations:
        with ThreadPoolExecutor(max_workers=min(8, len(locations))) as pool:
            districts = list(pool.map(fetch_one, locations))
    else:
        districts = []

    return jsonify({
        "districts": districts,
        "demo": current_app.config.get("DEMO_DATA", False),
    })


@views_bp.route("/news")
@login_required
def news():
    """Air-quality / environment headlines via Currents API (free tier).

    Real articles only, cached hourly - see services/news.py. If
    CURRENTS_API_KEY isn't set yet, the page shows a clear "not
    configured" state rather than any placeholder content.
    """
    return render_template("news.html", news=news_service.get_news())


@views_bp.route("/map")
@login_required
def map_view():
    """Interactive map: one real marker per region, colour-coded by live
    AQI. Built from the exact same overview cache the dashboard uses -
    no extra WeatherAPI calls, no separate boundary dataset to fetch or
    maintain - just each region's real administrative-centre
    coordinates (already in services/regions.py) plus its live reading.

    Every one of the 173 districts is also plotted (clustered, so it
    stays readable at country zoom) purely as a navigation pin - name
    and a link to that district's own page. Those pins are deliberately
    NOT colour-coded by AQI: showing a live-looking reading for all 173
    points would mean either 173 extra WeatherAPI calls on every map
    view (not free, not fast) or quietly reusing the parent region's
    number and presenting it as if it were that exact point's own
    reading, which would misrepresent precision that isn't real. A
    district's true live numbers are one tap away on its own page.
    """
    overview = openmeteo.get_overview()
    lang = getattr(g, "lang", DEFAULT_LANG)
    markers = [
        {
            "slug": r["slug"],
            "name": region_display_name(r, lang),
            "lat": r["lat"],
            "lon": r["lon"],
            "capital": r.get("capital"),
            "temp": r.get("temp"),
            "humidity": r.get("humidity"),
            "wind": r.get("wind"),
            "pm25": r.get("pm25"),
            "aqi": r.get("aqi"),
        }
        for r in overview.get("regions", [])
    ]
    district_markers = [
        {"id": loc.id, "name": loc.district_name, "lat": loc.latitude, "lon": loc.longitude}
        for loc in Location.query.order_by(Location.district_name).all()
    ]
    return render_template(
        "map.html", overview=overview, markers=markers, district_markers=district_markers
    )


@views_bp.route("/wildfires")
@login_required
def wildfires():
    """Active wildfire hotspots worldwide, from NASA FIRMS satellite
    detections (see services/wildfires.py). Real detections only, plus
    a same-day fire-danger index for Uzbekistan computed from the
    overview cache (no extra API calls)."""
    data = wildfires_service.get_wildfires()
    points = data.get("points") or []
    fire_stats = {
        "peak_frp": int(round(max((p.get("frp") or 0) for p in points))) if points else 0,
        "high_count": sum(1 for p in points if p.get("confidence") in ("h", "high")),
    }
    return render_template("wildfires.html", wildfires=data, fire_stats=fire_stats,
                           fire_risk=_uzbekistan_fire_risk())


def _uzbekistan_fire_risk():
    """Per-region fire-weather danger from data already in the overview.

    Uses the Angstrom index, a standard same-day fire-occurrence
    indicator computed from just air temperature and relative humidity:
        I = (humidity / 20) + ((27 - temperature) / 10)
    Below 2.0 fire occurrence is very likely (red); 2.0-2.4 likely
    (orange); 2.5-4.0 possible (yellow); above 4.0 unlikely (green).
    On top of that, a region that is BOTH fire-prone (I < 2.5) and windy
    (>= 25 km/h) gets a stubble-burning warning flag - burning crop
    residue ("ang'iz yoqish") in dry wind is the top human cause of
    field fires in Uzbekistan, and wind is what turns one into a blaze.

    Costs nothing: every number comes from the cached overview the
    dashboard already maintains - zero additional API calls.
    """
    overview = openmeteo.get_overview()
    rows = []
    for r in overview.get("regions", []):
        temp, humidity, wind = r.get("temp"), r.get("humidity"), r.get("wind")
        if temp is None or humidity is None:
            continue
        index = (humidity / 20.0) + ((27.0 - temp) / 10.0)
        if index < 2.0:
            tier = "red"
        elif index < 2.5:
            tier = "orange"
        elif index <= 4.0:
            tier = "yellow"
        else:
            tier = "green"
        rows.append({
            "slug": r["slug"], "name": r["name"],
            "index": round(index, 1), "tier": tier,
            "wind": wind,
            "burn_warning": index < 2.5 and (wind or 0) >= 25,
        })
    rows.sort(key=lambda x: x["index"])
    return {
        "regions": rows,
        "demo": overview.get("demo", False),
        "alert_count": sum(1 for x in rows if x["tier"] in ("red", "orange")),
        "burn_warnings": [x for x in rows if x["burn_warning"]],
    }


@views_bp.route("/storms")
@login_required
def storms():
    """Uzbekistan squall / dust-storm early warning: 24-hour peak wind
    gusts, dust load and pressure falls for all 14 regions, from
    Open-Meteo's free forecast APIs (see services/storms.py). This is
    the landlocked answer to a 'hurricanes' page: what actually hits
    Uzbekistan are violent wind squalls (dovul) and Aralkum dust
    storms, and both are forecastable."""
    return render_template("storms.html", storms=storms_service.get_storms())


_GREEN_SPACE_PATH = Path(__file__).parent / "data" / "green_space.json"
_green_space_cache = None


def _green_space():
    global _green_space_cache
    if _green_space_cache is None:
        try:
            _green_space_cache = json.loads(_GREEN_SPACE_PATH.read_text(encoding="utf-8"))
        except Exception:
            _green_space_cache = {"national": {}, "milestones": []}
    return _green_space_cache


MAX_PLEDGE_TREES = 1000


@views_bp.route("/trees", methods=["GET", "POST"])
@login_required
def trees():
    """Yashil Makon (Green Space) tracker.

    Two honest layers, clearly separated in the UI:
    1. OFFICIAL programme figures (1B+ trees since 2021, green-cover
       percentages, the Aral seabed greening target) from a curated,
       source-linked dataset - data/green_space.json - updated by hand
       as new official numbers are announced. Nothing is invented.
    2. The EcoPulse COMMUNITY counter: signed-in members log trees they
       have actually planted (capped at 1..1000 per entry so a typo
       can't fabricate a forest). Stored in the tree_pledges table.
    """
    if request.method == "POST":
        try:
            count = int(request.form.get("count", ""))
        except ValueError:
            count = 0
        region_slug = request.form.get("region") or None
        if region_slug and get_region(region_slug) is None:
            region_slug = None
        if 1 <= count <= MAX_PLEDGE_TREES:
            db.session.add(TreePledge(user_id=current_user.id, count=count,
                                      region_slug=region_slug))
            db.session.commit()
            flash("flash.pledge_saved", "message")
        else:
            flash("flash.pledge_invalid", "error")
        return redirect(url_for("views.trees"))

    community_total = db.session.query(
        db.func.coalesce(db.func.sum(TreePledge.count), 0)).scalar()
    pledge_count = db.session.query(db.func.count(TreePledge.id)).scalar()
    recent = [
        {"user_name": p.user.name, "count": p.count, "created_at": p.created_at,
         "region": get_region(p.region_slug) if p.region_slug else None}
        for p in (TreePledge.query.order_by(TreePledge.created_at.desc())
                  .limit(8).all())
    ]

    return render_template(
        "trees.html",
        green=_green_space(),
        community_total=community_total,
        pledge_count=pledge_count,
        recent_pledges=recent,
        max_pledge=MAX_PLEDGE_TREES,
    )


@views_bp.route("/hurricanes")
@login_required
def hurricanes():
    """Recent/active tropical cyclones worldwide, from GDACS (see
    services/hurricanes.py). Real events only."""
    data = hurricanes_service.get_hurricanes()
    storms = data.get("storms") or []
    counts = {"red": 0, "orange": 0, "green": 0}
    for s in storms:
        level = s.get("alert_level")
        if level in counts:
            counts[level] += 1
    return render_template("hurricanes.html", hurricanes=data, counts=counts)


# ---------------------------------------------------------------------------
# JSON API for the cascading searchable dropdowns
# ---------------------------------------------------------------------------

@views_bp.route("/api/my-location", methods=["POST"])
@login_required
def api_my_location():
    """Store the browser's geolocation on the user and return the nearest
    region so the picker can jump straight to local conditions."""
    data = request.get_json(silent=True) or {}
    try:
        lat = float(data["latitude"])
        lon = float(data["longitude"])
    except (KeyError, TypeError, ValueError):
        return jsonify({"error": "invalid coordinates"}), 400
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        return jsonify({"error": "out of range"}), 400

    nearest = min(REGIONS, key=lambda r: _haversine(lat, lon, r["lat"], r["lon"]))
    current_user.latitude = lat
    current_user.longitude = lon
    current_user.location_label = nearest["name"]
    db.session.commit()
    return jsonify({"region": nearest["name"],
                    "redirect": url_for("views.region", slug=nearest["slug"])})


def _haversine(lat1, lon1, lat2, lon2):
    """Great-circle distance in km between two points."""
    r = 6371
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


@views_bp.route("/api/regions")
@login_required
def api_regions():
    """Region list for the picker: {value, label} pairs.

    value is the raw data/districts.json key the districts endpoint
    below expects; label is the same name shown everywhere else in the
    active language (rname()/region_display_name()), so the picker no
    longer shows raw English dataset keys ("Andijan Region") in Uzbek
    mode. Sorted by the localized label, not the raw value.
    """
    lang = getattr(g, "lang", DEFAULT_LANG)
    rows = (db.session.query(Location.region_name).distinct().all())
    options = []
    for (name,) in rows:
        slug = slug_for_dataset_key(name)
        reg = get_region(slug) if slug else None
        label = region_display_name(reg, lang) if reg else name
        options.append({"value": name, "label": label})
    options.sort(key=lambda o: o["label"])
    # This list is fetched by the picker on EVERY single page in the app
    # (it lives in the shared topbar) but the underlying data - which
    # regions have districts - essentially never changes between
    # deploys. A short private browser cache means clicking around the
    # app after the first page load costs zero extra requests for this.
    response = jsonify(options)
    response.headers["Cache-Control"] = "private, max-age=300"
    return response


@views_bp.route("/api/regions/<path:region_name>/districts")
@login_required
def api_districts(region_name):
    """Alphabetical districts of one region, for the second dropdown."""
    rows = (Location.query.filter_by(region_name=region_name)
            .order_by(Location.district_name).all())
    if not rows:
        abort(404)
    response = jsonify([{"id": loc.id, "name": loc.district_name} for loc in rows])
    response.headers["Cache-Control"] = "private, max-age=300"
    return response
