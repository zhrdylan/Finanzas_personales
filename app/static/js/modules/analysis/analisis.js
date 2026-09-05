/**
 * Vista Análisis: predicción de gastos (hero), ahorro mensual (%) y tabla
 * de anomalías. Todos los cálculos provienen del módulo backend analysis
 * (Pandas/Scikit-learn) sobre datos reales del usuario.
 */

import { api } from "../../services/endpoints.js";
import { monedaActual } from "../../core/sesion.js";
import { el, ICONOS } from "../../utils/dom.js";
import { dinero, etiquetaMes, fechaCorta } from "../../utils/formato.js";
import { estadoVacio } from "../../utils/ui.js";
import { crearLineaPorcentaje, destruir } from "../dashboard/graficos.js";

function svgIcono(nombre) {
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("viewBox", "0 0 24 24");
  svg.setAttribute("fill", "none");
  svg.setAttribute("stroke", "currentColor");
  svg.setAttribute("stroke-width", "2");
  svg.setAttribute("stroke-linecap", "round");
  svg.setAttribute("stroke-linejoin", "round");
  svg.setAttribute("aria-hidden", "true");
  svg.innerHTML = ICONOS[nombre] || "";
  return svg;
}

export async function montarAnalisis(main) {
  const hero = main.querySelector("#hero-prediccion");
  const contAnomalias = main.querySelector("#anomalias-contenido");
  let graficoAhorro = null;

  estadoVacio(hero, "Calculando predicción…");

  try {
    const moneda = monedaActual();
    const [prediccion, evolucion, anomalias] = await Promise.all([
      api.panel.prediccion(moneda),
      api.panel.evolucion(moneda),
      api.panel.anomalias(),
    ]);

    /* --------------------------- Hero predicción --------------------------- */
    if (!prediccion.disponible) {
      hero.replaceChildren(
        el("div", { class: "hero-cuerpo" },
          el("h3", { class: "hero-titulo" }, svgIcono("cerebro"), "Predicción de gastos"),
          el("p", { class: "hero-nota" }, prediccion.mensaje ||
            "Necesitas al menos 2 meses de gastos para generar una predicción.")));
    } else {
      const distribucion = el("div", { class: "distribucion-proyectada" },
        el("p", { class: "distribucion-titulo" }, "Tendencia detectada"));

      const tendencias = {
        ascendente: "Tus gastos muestran una tendencia ascendente mes a mes.",
        descendente: "Tus gastos muestran una tendencia descendente mes a mes.",
        estable: "Tus gastos se mantienen estables mes a mes.",
      };
      distribucion.append(el("p", { class: "nota" },
        tendencias[prediccion.tendencia] || ""));

      hero.replaceChildren(
        el("div", { class: "hero-cuerpo" },
          el("h3", { class: "hero-titulo" }, svgIcono("cerebro"), "Predicción de gastos"),
          el("div", { style: { display: "flex", alignItems: "baseline", gap: "12px", flexWrap: "wrap" } },
            el("output", { class: "prediccion-valor texto-flujo" },
              dinero(prediccion.valor_predicho)),
            el("em", { class: "chip chip-lila" }, "Regresión lineal")),
          el("p", { class: "hero-nota" },
            "Gasto estimado para ",
            el("time", { datetime: prediccion.mes_predicho || "" },
              etiquetaMes(prediccion.mes_predicho || "")),
            " calculado con un modelo de regresión lineal sobre tu historial",
            ` (${prediccion.meses_analizados} meses analizados, R² = ${prediccion.r2 ?? "—"}).`,
            " Es una estimación simple, no un consejo financiero.")),
        distribucion);
    }

    /* --------------------------- Ahorro mensual (%) ------------------------ */
    const etiquetas = evolucion.meses.map(etiquetaMes);
    const porcentajes = evolucion.meses.map((_, i) => {
      const ingresos = Number(evolucion.ingresos[i] || 0);
      const gastos = Number(evolucion.gastos[i] || 0);
      return ingresos > 0 ? Math.round(((ingresos - gastos) / ingresos) * 1000) / 10 : 0;
    });
    const canvasAhorro = main.querySelector("#grafico-ahorro");
    graficoAhorro = crearLineaPorcentaje(canvasAhorro, etiquetas, porcentajes);

    /* ------------------------------ Anomalías ------------------------------ */
    if (!anomalias.disponible) {
      estadoVacio(contAnomalias, anomalias.mensaje ||
        `Se necesitan al menos ${anomalias.total_analizados} movimientos para el análisis.`);
    } else if (!anomalias.items.length) {
      estadoVacio(contAnomalias, anomalias.mensaje || "No se detectaron movimientos inusuales.");
    } else {
      const tabla = el("table", { class: "tabla-datos" },
        el("caption", { class: "solo-lectores" }, "Movimientos atípicos detectados"),
        el("thead", {}, el("tr", {},
          el("th", { scope: "col" }, "Fecha"),
          el("th", { scope: "col" }, "Categoría"),
          el("th", { scope: "col" }, "Concepto"),
          el("th", { scope: "col", class: "derecha" }, "Monto"),
          el("th", { scope: "col", class: "centro" }, "Puntuación"))),
        el("tbody", {}, anomalias.items.map((a) => el("tr", {},
          el("td", { class: "celda-fecha" },
            el("time", { datetime: a.fecha }, fechaCorta(a.fecha))),
          el("th", { scope: "row" }, a.categoria),
          el("td", {}, a.descripcion || "—"),
          el("td", { class: "celda-monto derecha" },
            el("data", { value: String(a.monto) }, dinero(a.monto))),
          el("td", { class: "centro" },
            el("data", {
              class: `etiqueta ${a.puntuacion >= 3 ? "etiqueta-critico" : "etiqueta-aviso"}`,
              value: String(a.puntuacion.toFixed(2)),
            }, a.puntuacion.toFixed(2)))))));

      contAnomalias.replaceChildren(
        el("div", { class: "tabla-resumen" },
          el("small", {}, `Método: ${anomalias.metodo || "—"}`),
          el("small", {}, `${anomalias.items.length} de ${anomalias.total_analizados} movimientos analizados`)),
        tabla,
        el("p", { class: "nota", style: { padding: "12px 24px" } },
          anomalias.umbral || ""));
    }
  } catch (error) {
    estadoVacio(hero, `No se pudo cargar el análisis: ${error.message}`);
    estadoVacio(contAnomalias, "Sin datos de anomalías.");
  }

  return () => { destruir(graficoAhorro); };
}
