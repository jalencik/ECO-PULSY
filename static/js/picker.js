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

  fetch("/api/regions")
    .then((r) => r.json())
    .then((names) => {
      region.addOptions(names.map((n) => ({ value: n, text: n })));
    })
    .catch(() => {});

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
