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

  // --- News thumbnail fallback ----------------------------------------------
  // Article images come from whatever CDN each source site happens to use;
  // a good share 404 or block hotlinking, and a broken <img> src just
  // renders empty space with nothing telling the visitor a photo was ever
  // meant to be there. One shared listener (capture phase, since "error"
  // doesn't bubble) swaps any failed article photo for the branded
  // EcoPulse placeholder instead of leaving a blank box.
  document.addEventListener("error", function (e) {
    var img = e.target;
    if (!img || !img.classList || !img.classList.contains("news-thumb")) return;
    var fallback = img.dataset.fallback;
    if (!fallback || img.src === fallback) return;
    img.src = fallback;
    img.classList.add("news-thumb-empty");
  }, true);

  // --- Owner-only secret reveal (admin panel) --------------------------------
  // The leadership roster (#admin-roster) is only ever rendered into the
  // page for the owner (server-side gate in admin.py), hidden by default.
  // Typing the secret word anywhere on the page (not inside an input)
  // toggles it. For every other visitor this whole block is inert -
  // the element simply doesn't exist in their DOM.
  var secretSection = document.getElementById("admin-roster");
  if (secretSection) {
    var SECRET_WORD = "administor";
    var typedBuffer = "";
    document.addEventListener("keydown", function (e) {
      var target = e.target;
      var tag = target && target.tagName ? target.tagName.toLowerCase() : "";
      if (tag === "input" || tag === "textarea" || tag === "select" || (target && target.isContentEditable)) return;
      if (!e.key || e.key.length !== 1 || e.ctrlKey || e.metaKey || e.altKey) return;
      typedBuffer = (typedBuffer + e.key.toLowerCase()).slice(-SECRET_WORD.length);
      if (typedBuffer === SECRET_WORD) {
        typedBuffer = "";
        secretSection.hidden = !secretSection.hidden;
        if (!secretSection.hidden) {
          secretSection.classList.remove("roster-reveal");
          void secretSection.offsetWidth; // restart the reveal animation
          secretSection.classList.add("roster-reveal");
          secretSection.scrollIntoView({ behavior: "smooth", block: "start" });
        }
      }
    });
  }

  // --- Audience role switcher (Public / Farmer / Expert) ---------------------
  // The same forecast means different actions for a parent, a farmer and
  // an analyst. Pages with role-specific guidance render ALL variants
  // server-side (so translations and CSP stay simple) inside
  // [data-role-view="public|farmer|expert"] blocks; these buttons just
  // toggle which one is visible. The choice is remembered per device.
  var roleButtons = document.querySelectorAll("[data-role-select]");
  if (roleButtons.length) {
    var applyRole = function (role) {
      roleButtons.forEach(function (b) {
        b.classList.toggle("active", b.dataset.roleSelect === role);
      });
      document.querySelectorAll("[data-role-view]").forEach(function (el) {
        el.hidden = el.dataset.roleView !== role;
      });
    };
    var savedRole;
    try { savedRole = localStorage.getItem("ecopulse-role"); } catch (e) { savedRole = null; }
    if (savedRole !== "public" && savedRole !== "farmer" && savedRole !== "expert") {
      savedRole = "public";
    }
    applyRole(savedRole);
    roleButtons.forEach(function (btn) {
      btn.addEventListener("click", function () {
        var role = btn.dataset.roleSelect;
        applyRole(role);
        try { localStorage.setItem("ecopulse-role", role); } catch (e) {}
      });
    });
  }

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
