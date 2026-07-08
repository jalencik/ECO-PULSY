/* Wildfire hotspot map (Leaflet + OpenStreetMap tiles).
 *
 * Every point is a real NASA FIRMS VIIRS active-fire detection from the
 * last 24 hours, nominal/high confidence only (see services/wildfires.py)
 * - nothing plotted here is estimated or invented. Colour marks detection
 * confidence (brighter red = high confidence), not fire size or danger.
 */
(function () {
  "use strict";

  var canvas = document.getElementById("wildfire-map-canvas");
  if (!canvas || typeof L === "undefined") return;

  var pointsEl = document.getElementById("wildfire-points");
  var i18nEl = document.getElementById("wildfire-i18n");
  var points = pointsEl ? JSON.parse(pointsEl.textContent) : [];
  var i18n = i18nEl ? JSON.parse(i18nEl.textContent) : {};

  var map = L.map(canvas, {
    scrollWheelZoom: false, touchZoom: true, tap: true, minZoom: 2,
  });
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: "&copy; <a href=\"https://www.openstreetmap.org/copyright\">OpenStreetMap</a> contributors",
    maxZoom: 10, minZoom: 2,
  }).addTo(map);

  // Same hover/trackpad-only scroll-zoom pattern as the main AQI map -
  // never hijacks the page scroll, still lets a trackpad pinch zoom.
  canvas.addEventListener("mouseenter", function () { map.scrollWheelZoom.enable(); });
  canvas.addEventListener("mouseleave", function () { map.scrollWheelZoom.disable(); });

  var bounds = [];
  points.forEach(function (p) {
    if (p.lat == null || p.lon == null) return;
    bounds.push([p.lat, p.lon]);

    var highConfidence = p.confidence === "h" || p.confidence === "high";
    var marker = L.circleMarker([p.lat, p.lon], {
      radius: 4,
      color: "#fff",
      weight: 1,
      fillColor: highConfidence ? "#c0392b" : "#e08a3e",
      fillOpacity: 0.85,
    }).addTo(map);

    var timeLabel = p.time && p.time.length === 4
      ? p.time.slice(0, 2) + ":" + p.time.slice(2) + " UTC" : "";
    var text = [p.date, timeLabel].filter(Boolean).join(" ")
      + (i18n.frpLabel && p.frp ? " · " + i18n.frpLabel + " " + Math.round(p.frp) : "");
    marker.bindTooltip(text, { direction: "top", offset: [0, -4] });
  });

  if (bounds.length) {
    map.fitBounds(bounds, { padding: [20, 20] });
  } else {
    map.setView([20, 10], 2);
  }
})();
