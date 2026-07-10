/* Tropical cyclone map (Leaflet + OpenStreetMap tiles).
 *
 * Every marker is a real GDACS tropical cyclone event's last reported
 * position (see services/hurricanes.py) - coloured by GDACS's own
 * alert level (green/orange/red), never invented.
 */
(function () {
  "use strict";

  var canvas = document.getElementById("hurricane-map-canvas");
  if (!canvas || typeof L === "undefined" || !window.EcoBasemap) return;

  var pointsEl = document.getElementById("storm-points");
  var storms = pointsEl ? JSON.parse(pointsEl.textContent) : [];

  var ALERT_COLORS = { green: "#3d8b48", orange: "#e08a3e", red: "#c0392b" };
  var NEUTRAL_COLOR = "#8a97a0";

  var map = L.map(canvas, {
    // tap:true is Leaflet's legacy iOS-Safari click shim; on modern
    // touchscreens it can swallow or double-fire real taps (see map.js
    // for the full explanation) so it's left off.
    scrollWheelZoom: false, touchZoom: true, tap: false, minZoom: 2,
  });
  // Theme-aware, English-labelled basemap (see basemap.js).
  window.EcoBasemap.attach(map, { maxZoom: 10, minZoom: 2 });

  canvas.addEventListener("mouseenter", function () { map.scrollWheelZoom.enable(); });
  canvas.addEventListener("mouseleave", function () { map.scrollWheelZoom.disable(); });

  var bounds = [];
  storms.forEach(function (s) {
    if (s.lat == null || s.lon == null) return;
    bounds.push([s.lat, s.lon]);

    var marker = L.circleMarker([s.lat, s.lon], {
      radius: 8,
      color: "#fff",
      weight: 2,
      fillColor: ALERT_COLORS[s.alert_level] || NEUTRAL_COLOR,
      fillOpacity: 0.9,
    }).addTo(map);
    marker.bindTooltip(s.name || "", { direction: "top", offset: [0, -8] });
  });

  if (bounds.length) {
    map.fitBounds(bounds, { padding: [30, 30] });
  } else {
    map.setView([20, 10], 2);
  }
})();
