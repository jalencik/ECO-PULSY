/* Shared UI behaviours: theme toggle, mobile sidebar, confirm dialogs. */
(function () {
  // --- Dark / light toggle -------------------------------------------------
  function setTheme(next) {
    document.documentElement.setAttribute("data-theme", next);
    try { localStorage.setItem("ecopulse-theme", next); } catch (e) {}
  }
  document.querySelectorAll("[data-theme-toggle]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var cur = document.documentElement.getAttribute("data-theme");
      setTheme(cur === "dark" ? "light" : "dark");
    });
  });

  // --- Mobile sidebar (burger) ---------------------------------------------
  var shell = document.querySelector(".shell");
  var burger = document.querySelector("[data-sidebar-toggle]");
  if (shell && burger) {
    burger.addEventListener("click", function () {
      shell.classList.toggle("sidebar-open");
    });
    var backdrop = document.querySelector("[data-sidebar-close]");
    if (backdrop) {
      backdrop.addEventListener("click", function () {
        shell.classList.remove("sidebar-open");
      });
    }
    // close after choosing a page
    document.querySelectorAll(".sidebar a").forEach(function (a) {
      a.addEventListener("click", function () {
        shell.classList.remove("sidebar-open");
      });
    });
  }

  // --- Expandable hourly forecast (region/location detail pages) -----------
  document.querySelectorAll("[data-day-toggle]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var strip = btn.nextElementSibling;
      if (!strip || !strip.classList.contains("hour-strip")) return;
      var open = strip.classList.toggle("open");
      btn.setAttribute("aria-expanded", open ? "true" : "false");
    });
  });

  // --- CSP-safe confirm dialogs (replaces inline onsubmit) ------------------
  document.querySelectorAll("form[data-confirm]").forEach(function (form) {
    form.addEventListener("submit", function (event) {
      if (!window.confirm(form.getAttribute("data-confirm"))) {
        event.preventDefault();
      }
    });
  });

  // --- Casual copy-paste friction -------------------------------------------
  // IMPORTANT, please read: this is friction, not protection. No website
  // can block view-source, browser devtools or curl with client-side
  // JS - the browser always has the full HTML/CSS/JS it was sent, for
  // every site on the internet, including this one. Anyone who opens
  // devtools from the browser's own menu (or just disables JavaScript)
  // bypasses this instantly. What actually keeps this app safe is that
  // secrets (the WeatherAPI key, database URL, session secret key) live
  // only in server environment variables and are never sent to the
  // browser - that's true with or without the block below. Delete this
  // block anytime it gets in the way of legitimate use (copying an
  // error message, right-click "open in new tab", accessibility tools).
  document.addEventListener("contextmenu", function (e) { e.preventDefault(); });
  document.addEventListener("keydown", function (e) {
    var key = e.key ? e.key.toLowerCase() : "";
    var blockedCombo = (e.ctrlKey || e.metaKey) &&
      (key === "u" || (e.shiftKey && (key === "i" || key === "j" || key === "c")));
    if (key === "f12" || blockedCombo) e.preventDefault();
  });
})();
