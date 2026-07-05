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
    placeholder: "District…",
  });
  district.disable();

  const region = new TomSelect(wrap.querySelector("[data-picker-region]"), {
    ...settings,
    placeholder: "Region…",
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
})();
