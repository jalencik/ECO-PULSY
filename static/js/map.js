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
  var i18nEl = document.getElementById("map-i18n");
  var markers = markersEl ? JSON.parse(markersEl.textContent) : [];
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
  var NEUTRAL_COLOR = "#8a97a0";

  var map = L.map(canvas, { scrollWheelZoom: false });
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: "&copy; <a href=\"https://www.openstreetmap.org/copyright\">OpenStreetMap</a> contributors",
    maxZoom: 12,
    minZoom: 4,
  }).addTo(map);

  var bounds = [];

  markers.forEach(function (m) {
    if (m.lat == null || m.lon == null) return;
    bounds.push([m.lat, m.lon]);

    var color = m.aqi ? (AQI_COLORS[m.aqi.css] || NEUTRAL_COLOR) : NEUTRAL_COLOR;
    var marker = L.circleMarker([m.lat, m.lon], {
      radius: 11,
      color: "#fff",
      weight: 2,
      fillColor: color,
      fillOpacity: 0.92,
    }).addTo(map);

    // Rich card on hover (desktop) via a tooltip, and the same card on
    // tap via a popup (touch devices, and anyone who prefers to click)
    // - two independent DOM trees since each binding owns its own node.
    marker.bindTooltip(buildPopup(m), {
      direction: "top", offset: [0, -12], interactive: true, className: "map-tooltip-rich",
    });
    marker.bindPopup(buildPopup(m), { className: "map-popup-wrap" });
  });

  if (bounds.length) {
    map.fitBounds(bounds, { padding: [30, 30] });
  } else {
    map.setView([41.3, 64.5], 5);
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
