/* Cascading searchable location picker (Tom Select).
   Region first; the district list loads for that region only, sorted
   alphabetically server-side. Picking a district opens its page. */
(function () {
  const wrap = document.querySelector("[data-picker]");
  if (!wrap || typeof TomSelect === "undefined") return;

  const settings = {
    maxItems: 1,
    maxOptions: 200,
    sortField: { field: "text", direction: "asc" },
    // Render the option list on <body> instead of nesting it inside the
    // topbar. The picker sits inside several stacked flex/positioned
    // containers (topbar -> topbar-right -> picker), and on pages with
    // their own positioned content below (map, ranking rows, news
    // cards) a nested dropdown can end up visually clipped or covered.
    // Appending to <body> sidesteps that entirely, regardless of what
    // the rest of the page looks like.
    dropdownParent: "body",
  };

  const district = new TomSelect(wrap.querySelector("[data-picker-district]"), {
    ...settings,
    placeholder: wrap.dataset.tDistrict || "District…",
  });
  district.disable();

  const region = new TomSelect(wrap.querySelector("[data-picker-region]"), {
    ...settings,
    placeholder: wrap.dataset.tRegion || "Region…",
  });

  // {value, label} pairs, already localized and sorted server-side (see
  // views.api_regions) so the picker shows the same names as the rest
  // of the app instead of raw English dataset keys.
  fetch("/api/regions")
    .then((r) => r.json())
    .then((options) => {
      region.addOptions(options.map((o) => ({ value: o.value, text: o.label })));
    })
    .catch(function (err) {
      console.warn("EcoPulse: could not load the region list for the picker.", err);
    });

  region.on("change", (value) => {
    district.clear(true);
    district.clearOptions();
    if (!value) {
      district.disable();
      return;
    }
    fetch("/api/regions/" + encodeURIComponent(value) + "/districts")
      .then((r) => r.json())
      .then((list) => {
        district.addOptions(list.map((d) => ({ value: String(d.id), text: d.name })));
        district.enable();
        district.open();
      })
      .catch(() => {});
  });

  district.on("change", (id) => {
    if (id) window.location.href = "/locations/" + id;
  });

  // "Use my current location" — asks the browser, stores it, jumps to the
  // nearest region.
  const locBtn = wrap.querySelector("[data-my-location]");
  if (locBtn && navigator.geolocation) {
    locBtn.addEventListener("click", () => {
      locBtn.classList.add("loading");
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          fetch("/api/my-location", {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              "X-CSRFToken": wrap.getAttribute("data-csrf") || "",
            },
            body: JSON.stringify({
              latitude: pos.coords.latitude,
              longitude: pos.coords.longitude,
            }),
          })
            .then((r) => r.json())
            .then((d) => {
              if (d.redirect) window.location.href = d.redirect;
              else locBtn.classList.remove("loading");
            })
            .catch(() => locBtn.classList.remove("loading"));
        },
        () => {
          locBtn.classList.remove("loading");
          alert(wrap.dataset.tLocationError || "Could not get your location. Please allow location access.");
        }
      );
    });
  }
})();
