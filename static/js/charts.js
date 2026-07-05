/* Renders the 48-hour temperature / PM2.5 trend chart on region pages. */
(function () {
  const dataEl = document.getElementById("chart-data");
  const canvas = document.getElementById("trend-chart");
  if (!dataEl || !canvas || typeof Chart === "undefined") return;

  const series = JSON.parse(dataEl.textContent);
  const labels = series.times.map(function (t) {
    const d = new Date(t);
    return d.getHours().toString().padStart(2, "0") + ":00";
  });

  new Chart(canvas, {
    type: "line",
    data: {
      labels: labels,
      datasets: [
        {
          label: "Temperature (°C)",
          data: series.temp,
          borderColor: "#e8630a",
          backgroundColor: "transparent",
          yAxisID: "temp",
          tension: 0.35,
          pointRadius: 0,
          borderWidth: 2,
        },
        {
          label: "PM2.5 (µg/m³)",
          data: series.pm25,
          borderColor: "#0e5a6d",
          backgroundColor: "rgba(14, 90, 109, 0.08)",
          fill: true,
          yAxisID: "pm",
          tension: 0.35,
          pointRadius: 0,
          borderWidth: 2,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: "index", intersect: false },
      plugins: {
        legend: { labels: { usePointStyle: true, boxHeight: 6 } },
      },
      scales: {
        x: { grid: { display: false }, ticks: { maxTicksLimit: 12 } },
        temp: {
          position: "left",
          title: { display: true, text: "°C" },
          grid: { color: "rgba(0,0,0,0.05)" },
        },
        pm: {
          position: "right",
          title: { display: true, text: "µg/m³" },
          grid: { display: false },
          beginAtZero: true,
        },
      },
    },
  });
})();
