/* Shared Leaflet basemap for every map in the app (AQI map, wildfires,
 * hurricanes).
 *
 * CARTO's raster basemaps are used instead of the default
 * openstreetmap.org tiles for two concrete reasons:
 *
 * 1. English labels. OSM's default style labels every country in its
 *    local language/script ("Тоҷикистон", "قزاقستان"), which read as
 *    unprofessional noise to most visitors here. CARTO's cartography
 *    prefers English names worldwide.
 * 2. Dark mode. The app defaults to a dark theme, and a bright beige
 *    map embedded in a dark page glares. CARTO ships a proper dark
 *    basemap (dark_all) that matches the app's palette; the light
 *    theme gets Voyager, a clean modern light style.
 *
 * The active tile layer follows the app theme live: flipping the
 * moon/sun toggle swaps the basemap in place, no reload needed
 * (a MutationObserver watches the data-theme attribute theme.js/ui.js
 * maintain on <html>).
 *
 * CARTO's free basemap tier is explicitly available for non-commercial
 * / small-scale use with attribution, which the attribution control
 * carries. Tiles are plain <img> requests, already allowed by the CSP
 * (img-src https:).
 */
(function () {
  "use strict";

  var LIGHT_URL = "https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png";
  var DARK_URL = "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png";
  var ATTRIBUTION =
    '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors ' +
    '&copy; <a href="https://carto.com/attributions">CARTO</a>';

  function isDark() {
    return document.documentElement.getAttribute("data-theme") === "dark";
  }

  window.EcoBasemap = {
    /* Adds the theme-aware tile layer to a Leaflet map. Call once per
       map, right after L.map(). Options: minZoom / maxZoom forwarded
       to the tile layer. */
    attach: function (map, options) {
      options = options || {};
      var layer = null;

      function setLayer() {
        if (layer) map.removeLayer(layer);
        layer = L.tileLayer(isDark() ? DARK_URL : LIGHT_URL, {
          attribution: ATTRIBUTION,
          subdomains: "abcd",
          minZoom: options.minZoom != null ? options.minZoom : 2,
          maxZoom: options.maxZoom != null ? options.maxZoom : 18,
        }).addTo(map);
        layer.bringToBack(); // keep data markers above the basemap
      }

      setLayer();

      new MutationObserver(function (mutations) {
        for (var i = 0; i < mutations.length; i++) {
          if (mutations[i].attributeName === "data-theme") { setLayer(); return; }
        }
      }).observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
    },
  };
})();
