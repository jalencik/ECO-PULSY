/* Interactive regions map (Leaflet + OpenStreetMap tiles).
 *
 * Every marker sits at a region's real administrative-centre coordinate
 * (services/regions.py) and every number in its popup comes straight
 * from the same cached overview the dashboard uses - nothing on this
 * page is estimated or invented. If a marker has no AQI yet (a region
 * WeatherAPI briefly failed to answer for), it's still shown, just
 * coloured neutral instead of guessing a category.
 */
(function () {
  "use strict";

  var canvas = document.getElementById("map-canvas");
  if (!canvas || typeof L === "undefined") return;

  var markersEl = document.getElementById("map-markers");
  var districtsEl = document.getElementById("map-districts");
  var i18nEl = document.getElementById("map-i18n");
  var markers = markersEl ? JSON.parse(markersEl.textContent) : [];
  var districts = districtsEl ? JSON.parse(districtsEl.textContent) : [];
  var i18n = i18nEl ? JSON.parse(i18nEl.textContent) : {};

  // Mirrors the --aqi-* custom properties in main.css. Leaflet's SVG
  // renderer needs literal colour values, not CSS variables.
  var AQI_COLORS = {
    "aqi-good": "#3d8b48",
    "aqi-moderate": "#b8860b",
    "aqi-usg": "#d2691e",
    "aqi-unhealthy": "#c0392b",
    "aqi-very-unhealthy": "#8e44ad",
    "aqi-hazardous": "#7b1e3b",
  };
  var AQI_FACES = {
    "aqi-good": "face-good",
    "aqi-moderate": "face-moderate",
    "aqi-usg": "face-usg",
    "aqi-unhealthy": "face-unhealthy",
    "aqi-very-unhealthy": "face-very-unhealthy",
    "aqi-hazardous": "face-hazardous",
  };
  var NEUTRAL_COLOR = "#8a97a0";

  // Real, approximate Uzbekistan extent (37.0-45.8 N, 55.7-73.3 E) with a
  // little padding - keeps panning/zooming focused on the country instead
  // of drifting off into Kazakhstan, Turkmenistan, China etc. This is a
  // viewport limit only, not a claim about exact border geometry.
  var UZ_BOUNDS = L.latLngBounds([36.9, 55.6], [45.9, 73.4]);

  var map = L.map(canvas, {
    scrollWheelZoom: false, // enabled on hover/touch below, so it never hijacks page scroll
    touchZoom: true,        // pinch-to-zoom on phones/tablets (Leaflet default, set explicitly)
    // Leaflet's legacy "tap" shim re-synthesizes click events from
    // touchstart/touchend to work around a 300ms-delay bug in iOS Safari
    // ~10 years ago. Every modern mobile browser fires real click events
    // on tap without that delay, and this shim's own event replay can
    // itself swallow or double-fire a genuine tap - real-device testing
    // here showed marker taps intermittently doing nothing at all with
    // it enabled. Leaving it off lets native tap/click events through
    // untouched, which is what makes marker taps reliable on phones.
    tap: false,
    maxBounds: UZ_BOUNDS,
    // A fully "solid" (1.0) edge also blocks Leaflet's own autoPan from
    // nudging the map when a popup near the border would otherwise open
    // partly outside the map card and get clipped by its rounded-corner
    // overflow. 0.8 keeps dragging from drifting off-country while still
    // leaving autoPan enough give to fully reveal an edge popup.
    maxBoundsViscosity: 0.8,
    minZoom: 5,
  });
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: "&copy; <a href=\"https://www.openstreetmap.org/copyright\">OpenStreetMap</a> contributors",
    maxZoom: 15,
    minZoom: 5,
  }).addTo(map);

  // Trackpad "pinch" gestures (and plain mouse wheel) only zoom the map
  // while the cursor is actually over it - otherwise scrolling the page
  // past the map would get hijacked. Real finger pinch on touchscreens
  // is unaffected (touchZoom above handles that independently).
  canvas.addEventListener("mouseenter", function () { map.scrollWheelZoom.enable(); });
  canvas.addEventListener("mouseleave", function () { map.scrollWheelZoom.disable(); });

  var bounds = [];

  // Touch devices have no hover, and Leaflet opens a click-bound tooltip
  // AND a click-bound popup from the exact same tap - two overlapping
  // copies of the same card fighting for the touch, which is what made
  // this map feel broken on phones. Hover tooltips are desktop-only;
  // touch always gets a single clean tap-to-open popup.
  var canHover = !L.Browser.touch;
  var markerRadius = L.Browser.touch ? 19 : 11;
  // Cap how wide a popup card can render relative to the map's own
  // width - on a narrow phone a fixed 210-320px popup can be wider than
  // the map itself, which is what forces a large autoPan (or clips) near
  // any edge. Keeping it a bit narrower than the canvas means most
  // popups fit without needing to pan the map at all.
  var popupMaxWidth = Math.max(190, Math.min(300, canvas.clientWidth - 40));

  markers.forEach(function (m) {
    if (m.lat == null || m.lon == null) return;
    bounds.push([m.lat, m.lon]);

    var color = m.aqi ? (AQI_COLORS[m.aqi.css] || NEUTRAL_COLOR) : NEUTRAL_COLOR;
    var marker = L.circleMarker([m.lat, m.lon], {
      radius: markerRadius,
      color: "#fff",
      weight: 2,
      fillColor: color,
      fillOpacity: 0.92,
    }).addTo(map);

    if (canHover) {
      marker.bindTooltip(buildPopup(m), {
        direction: "top", offset: [0, -12], interactive: true, className: "map-tooltip-rich",
      });
    }
    marker.bindPopup(buildPopup(m), {
      className: "map-popup-wrap", autoPanPadding: [24, 24], maxWidth: popupMaxWidth,
    });
  });

  // District pins: every one of the 173 districts, clustered so the map
  // stays readable at country zoom and only breaks apart into individual
  // pins once you zoom into a cluster. Deliberately plain/neutral (see
  // the comment in views.map_view for why these don't carry a live AQI
  // colour) - tap one to open that district's own page for its real
  // current numbers.
  if (districts.length && typeof L.markerClusterGroup === "function") {
    var clusterGroup = L.markerClusterGroup({
      maxClusterRadius: 42,
      spiderfyOnMaxZoom: true,
      disableClusteringAtZoom: 11,
    });
    // The visible dot stays a small 9px so the map doesn't look cluttered,
    // but the tappable icon box itself is larger on touch devices (a 9px
    // target is well under the ~44px minimum comfortable touch size).
    var iconBox = L.Browser.touch ? 30 : 10;
    var districtIcon = L.divIcon({
      className: "map-district-icon",
      html: '<span class="map-district-dot"></span>',
      iconSize: [iconBox, iconBox],
      iconAnchor: [iconBox / 2, iconBox / 2],
    });
    districts.forEach(function (d) {
      if (d.lat == null || d.lon == null) return;
      var pin = L.marker([d.lat, d.lon], { icon: districtIcon });
      if (canHover) pin.bindTooltip(d.name, { direction: "top", offset: [0, -4] });
      pin.on("click", function () { window.location.href = "/locations/" + d.id; });
      clusterGroup.addLayer(pin);
    });
    map.addLayer(clusterGroup);
  }

  if (bounds.length) {
    map.fitBounds(bounds, { padding: [30, 30] });
  } else {
    map.fitBounds(UZ_BOUNDS);
  }

  function buildPopup(m) {
    var box = document.createElement("div");
    box.className = "map-popup";

    var title = document.createElement("h4");
    title.textContent = m.name;
    box.appendChild(title);

    if (m.capital) {
      var sub = document.createElement("p");
      sub.className = "muted small";
      sub.textContent = i18n.measuredAt + " " + m.capital;
      box.appendChild(sub);
    }

    if (m.aqi) {
      var chipRow = document.createElement("div");
      chipRow.className = "map-popup-aqi";

      var faceId = AQI_FACES[m.aqi.css];
      if (faceId) {
        var faceWrap = document.createElement("span");
        faceWrap.className = "aqi-face " + m.aqi.css;
        var faceSvg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
        faceSvg.setAttribute("width", "20");
        faceSvg.setAttribute("height", "20");
        var use = document.createElementNS("http://www.w3.org/2000/svg", "use");
        use.setAttributeNS("http://www.w3.org/1999/xlink", "href", "#" + faceId);
        use.setAttribute("href", "#" + faceId);
        faceSvg.appendChild(use);
        faceWrap.appendChild(faceSvg);
        chipRow.appendChild(faceWrap);
      }

      var chip = document.createElement("span");
      chip.className = "chip " + m.aqi.css;
      chip.textContent = "AQI " + m.aqi.value;
      chip.title = i18n.aqiHint || "";
      chipRow.appendChild(chip);
      var label = document.createElement("span");
      label.className = "muted small";
      label.textContent = m.aqi.label;
      chipRow.appendChild(label);
      box.appendChild(chipRow);
    }

    var stats = document.createElement("div");
    stats.className = "map-popup-stats";
    stats.appendChild(statRow(m.temp != null ? Math.round(m.temp) + "°C" : "–"));
    stats.appendChild(statRow((m.humidity != null ? m.humidity : "–") + "% " + i18n.humidity));
    stats.appendChild(statRow((m.wind != null ? Math.round(m.wind) : "–") + " km/h " + i18n.wind));
    if (m.pm25 != null) stats.appendChild(statRow("PM2.5 " + m.pm25));
    box.appendChild(stats);

    var link = document.createElement("a");
    link.href = "/regions/" + m.slug;
    link.className = "map-popup-link";
    link.textContent = i18n.viewDetails + " →";
    box.appendChild(link);

    return box;
  }

  function statRow(text) {
    var span = document.createElement("span");
    span.textContent = text;
    return span;
  }
})();
