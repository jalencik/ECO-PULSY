/* Theme bootstrap — runs before first paint so there's no flash.
   Loaded synchronously in <head> on purpose.

   Default (no explicit choice saved yet): light/white on public and
   auth pages (landing, sign in, sign up), dark/black once signed in -
   set via the data-authed attribute base.html renders on <html> from
   the real server-side auth state. Anyone who manually flips the
   moon/sun toggle (see ui.js) always keeps that explicit choice from
   then on, on that device, regardless of auth state. */
(function () {
  var saved;
  try { saved = localStorage.getItem("ecopulse-theme"); } catch (e) { saved = null; }
  if (saved !== "dark" && saved !== "light") {
    var authed = document.documentElement.getAttribute("data-authed") === "true";
    saved = authed ? "dark" : "light";
  }
  document.documentElement.setAttribute("data-theme", saved);
})();
