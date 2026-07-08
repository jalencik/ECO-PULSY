/* Tropical cyclone map (Leaflet + OpenStreetMap tiles).
 *
 * Every marker is a real GDACS tropical cyclone event's last reported
 * position (see services/hurricanes.py) - coloured by GDACS's own
 * alert level (green/orange/red), never invented.
 */
(function () {
  "use strict";

  var canvas = document.getElementById("hurricane-map-canvas");
  if (!canvas || typeof L === "undefined") return;

  var pointsEl = document.getElementById("storm-points");
  var storms = pointsEl ? JSON.parse(pointsEl.textContent) : [];

  var ALERT_COLORS = { green: "#3d8b48", orange: "#e08a3e", red: "#c0392b" };
  var NEUTRAL_COLOR = "#8a97a0";

  var map = L.map(canvas, {
    scrollWheelZoom: false, touchZoom: true, tap: true, minZoom: 2,
  });
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: "&copy; <a href=\"https://www.openstreetmap.org/copyright\">OpenStreetMap</a> contributors",
    maxZoom: 10, minZoom: 2,
  }).addTo(map);

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
