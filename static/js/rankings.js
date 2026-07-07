/* Rankings page: tab switching + lazy per-region district expand.
 *
 * Each region row appears once per tab (its rank differs per metric), so
 * expand/collapse state is tracked per (metric, region) pair. The actual
 * district data is fetched at most once per region no matter how many
 * tabs it's expanded in - the fetch is cached client-side in
 * `districtCache`, and server-side get_detail() caches it again, so a
 * popular region only ever costs one real WeatherAPI round-trip within
 * the cache window.
 */
(function () {
  "use strict";

  var METRIC_GETTERS = {
    hottest: function (d) { return d.temp; },
    polluted: function (d) { return d.aqi ? d.aqi.value : null; },
    humid: function (d) { return d.humidity; },
    windy: function (d) { return d.wind; },
  };

  var districtCache = {}; // region slug -> array of district dicts

  function formatValue(metric, d) {
    if (metric === "hottest") {
      return (d.temp != null ? Math.round(d.temp) : "–") + "°";
    }
    if (metric === "humid") {
      return (d.humidity != null ? Math.round(d.humidity) : "–") + "%";
    }
    if (metric === "windy") {
      return (d.wind != null ? Math.round(d.wind) : "–") + " km/h";
    }
    if (metric === "polluted") {
      return d.aqi ? "AQI " + d.aqi.value : "–";
    }
    return "–";
  }

  function chipClass(metric, d) {
    return metric === "polluted" && d.aqi ? d.aqi.css : "chip-neutral";
  }

  function renderDistricts(container, metric, districts) {
    var getter = METRIC_GETTERS[metric];
    var usable = districts.filter(function (d) {
      return !d.error && getter(d) != null;
    });
    usable.sort(function (a, b) { return getter(b) - getter(a); });

    if (!usable.length) {
      container.textContent = container.dataset.emptyText;
      return;
    }

    container.innerHTML = usable.map(function (d, i) {
      return (
        '<div class="rank-row-sub' + (d.stale ? " rank-row-stale" : "") + '">' +
          '<span class="rank-num">' + (i + 1) + "</span>" +
          '<span class="rank-name"></span>' +
          '<span class="chip ' + chipClass(metric, d) + '"></span>' +
        "</div>"
      );
    }).join("");

    // Fill text nodes via textContent (not string concat) so district
    // names can never be interpreted as HTML.
    var rows = container.querySelectorAll(".rank-row-sub");
    usable.forEach(function (d, i) {
      if (d.stale) rows[i].title = container.dataset.staleText || "";
      rows[i].querySelector(".rank-name").textContent = d.name;
      rows[i].querySelector(".chip").textContent = formatValue(metric, d);
    });
  }

  function loadDistricts(slug, container, metric) {
    if (districtCache[slug]) {
      renderDistricts(container, metric, districtCache[slug]);
      return;
    }
    container.textContent = container.dataset.loadingText;
    fetch("/api/rankings/" + encodeURIComponent(slug) + "/districts")
      .then(function (r) {
        if (!r.ok) throw new Error("bad response");
        return r.json();
      })
      .then(function (data) {
        districtCache[slug] = data.districts || [];
        renderDistricts(container, metric, districtCache[slug]);
      })
      .catch(function () {
        container.textContent = container.dataset.errorText;
      });
  }

  document.querySelectorAll(".ranking-tab").forEach(function (tab) {
    tab.addEventListener("click", function () {
      document.querySelectorAll(".ranking-tab").forEach(function (t) {
        t.classList.remove("active");
      });
      document.querySelectorAll(".ranking-panel").forEach(function (p) {
        p.classList.remove("active");
      });
      tab.classList.add("active");
      var panel = document.getElementById("panel-" + tab.dataset.metric);
      if (panel) panel.classList.add("active");
    });
  });

  function toggleRow(row) {
    var metric = row.dataset.metric;
    var slug = row.dataset.slug;
    var sub = document.getElementById("districts-" + metric + "-" + slug);
    if (!sub) return;
    var expanded = row.classList.toggle("expanded");
    row.setAttribute("aria-expanded", expanded ? "true" : "false");
    sub.classList.toggle("open", expanded);
    if (expanded) loadDistricts(slug, sub, metric);
  }

  document.querySelectorAll(".rank-row[data-slug]").forEach(function (row) {
    row.addEventListener("click", function () { toggleRow(row); });
    row.addEventListener("keydown", function (e) {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        toggleRow(row);
      }
    });
  });
})();
