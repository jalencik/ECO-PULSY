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

  // --- CSP-safe confirm dialogs (replaces inline onsubmit) ------------------
  document.querySelectorAll("form[data-confirm]").forEach(function (form) {
    form.addEventListener("submit", function (event) {
      if (!window.confirm(form.getAttribute("data-confirm"))) {
        event.preventDefault();
      }
    });
  });
})();
