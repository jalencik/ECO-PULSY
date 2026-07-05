/* Theme bootstrap — runs before first paint so there's no flash.
   Loaded synchronously in <head> on purpose. */
(function () {
  var saved;
  try { saved = localStorage.getItem("ecopulse-theme"); } catch (e) { saved = null; }
  if (saved !== "dark" && saved !== "light") {
    saved = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches
      ? "dark" : "light";
  }
  document.documentElement.setAttribute("data-theme", saved);
})();
