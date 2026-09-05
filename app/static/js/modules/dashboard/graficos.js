/**
 * Gráficos del panel con Chart.js (servido localmente, sin CDN).
 * Encapsula la construcción y destrucción de los gráficos.
 */

/** Opciones comunes: sin animaciones excesivas, tooltip formateado. */
function opcionesBase(formateador) {
  return {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      tooltip: {
        backgroundColor: "#0d1843",
        padding: 10,
        cornerRadius: 10,
        callbacks: {
          label: (ctx) => ` ${formateador(ctx.parsed)}`,
        },
      },
    },
  };
}

/** Gráfico de dona: gastos por categoría. */
export function crearDona(canvas, datos, formateador) {
  return new Chart(canvas, {
    type: "doughnut",
    data: {
      labels: datos.map((d) => d.nombre),
      datasets: [{
        data: datos.map((d) => Number(d.total)),
        backgroundColor: datos.map((d) => d.color),
        borderColor: "#ffffff",
        borderWidth: 2,
        hoverOffset: 6,
        cutout: "72%",
      }],
    },
    options: {
      ...opcionesBase(formateador),
      onClick: (_evt, elementos) => {
        // foco accesible: nada que hacer, tooltip nativo
      },
    },
  });
}

/** Gráfico de línea: ingresos vs gastos (6 meses). */
export function crearLinea(canvas, evolucion, formateador) {
  return new Chart(canvas, {
    type: "line",
    data: {
      labels: evolucion.meses,
      datasets: [
        {
          label: "Ingresos",
          data: evolucion.ingresos.map(Number),
          borderColor: "#0053ce",
          backgroundColor: "rgba(81, 217, 254, 0.12)",
          fill: true,
          tension: 0.4,
          borderWidth: 3,
          pointRadius: 3,
          pointBackgroundColor: "#0053ce",
        },
        {
          label: "Gastos",
          data: evolucion.gastos.map(Number),
          borderColor: "#E5484D",
          borderDash: [6, 6],
          fill: false,
          tension: 0.4,
          borderWidth: 2.5,
          pointRadius: 3,
          pointBackgroundColor: "#E5484D",
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: "index", intersect: false },
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: "#0d1843",
          padding: 10,
          cornerRadius: 10,
          callbacks: { label: (ctx) => ` ${ctx.dataset.label}: ${formateador(ctx.parsed.y)}` },
        },
      },
      scales: {
        y: {
          ticks: { callback: (v) => formateador(v), color: "#737686", font: { size: 11 } },
          grid: { color: "rgba(194, 198, 215, 0.25)" },
        },
        x: { ticks: { color: "#737686", font: { size: 11 } }, grid: { display: false } },
      },
    },
  });
}

/** Gráfico de línea: ahorro mensual (%). */
export function crearLineaPorcentaje(canvas, etiquetas, valores) {
  return new Chart(canvas, {
    type: "line",
    data: {
      labels: etiquetas,
      datasets: [{
        label: "Ahorro",
        data: valores,
        borderColor: "#55ddac",
        backgroundColor: "rgba(85, 221, 172, 0.25)",
        fill: true,
        tension: 0.4,
        borderWidth: 3,
        pointRadius: 3,
        pointBackgroundColor: "#55ddac",
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: "#0d1843",
          padding: 10,
          cornerRadius: 10,
          callbacks: { label: (ctx) => ` ${ctx.parsed.y.toFixed(1)}%` },
        },
      },
      scales: {
        y: {
          ticks: { callback: (v) => `${v}%`, color: "#737686", font: { size: 11 } },
          grid: { color: "rgba(194, 198, 215, 0.25)" },
        },
        x: { ticks: { color: "#737686", font: { size: 11 } }, grid: { display: false } },
      },
    },
  });
}

/** Destruye un gráfico de forma segura. */
export function destruir(grafico) {
  grafico?.destroy?.();
}
