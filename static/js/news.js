/* News page: client-side category filtering for the curated library.
 *
 * Pure show/hide over cards already in the DOM - no fetches, no
 * re-rendering, instant on any device. The category value lives in a
 * data attribute on each card; "all" clears the filter.
 */
(function () {
  "use strict";

  var grid = document.getElementById("curated-grid");
  if (!grid) return;

  var filters = document.querySelectorAll(".news-filter");
  var cards = grid.querySelectorAll(".news-card-story");

  filters.forEach(function (btn) {
    btn.addEventListener("click", function () {
      filters.forEach(function (b) { b.classList.remove("active"); });
      btn.classList.add("active");
      var category = btn.dataset.category;
      cards.forEach(function (card) {
        card.hidden = category !== "all" && card.dataset.category !== category;
      });
    });
  });
})();
