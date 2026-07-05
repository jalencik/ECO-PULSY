"""Public pages, the dashboard, region and district pages, and the
small JSON API that powers the cascading location picker."""
import math

from flask import (Blueprint, abort, jsonify, redirect, render_template,
                   request, url_for)
from flask_login import current_user, login_required

from extensions import db
from models import Location
from services import openmeteo
from services.regions import REGIONS, get_region, slug_for_dataset_key

views_bp = Blueprint("views", __name__)


@views_bp.route("/")
def index():
    """Landing page (logged-in users go straight to their dashboard)."""
    if current_user.is_authenticated:
        return redirect(url_for("views.dashboard"))
    return render_template("index.html")


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
    """Alphabetical list of region names that have districts."""
    rows = (db.session.query(Location.region_name)
            .distinct().order_by(Location.region_name).all())
    return jsonify([row[0] for row in rows])


@views_bp.route("/api/regions/<path:region_name>/districts")
@login_required
def api_districts(region_name):
    """Alphabetical districts of one region, for the second dropdown."""
    rows = (Location.query.filter_by(region_name=region_name)
            .order_by(Location.district_name).all())
    if not rows:
        abort(404)
    return jsonify([{"id": loc.id, "name": loc.district_name} for loc in rows])
