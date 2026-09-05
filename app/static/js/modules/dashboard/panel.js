/**
 * Vista Resumen (panel): KPIs, banner de anomalías, gráficos y recientes.
 * Todos los datos provienen de la API del usuario autenticado (sin mock).
 */

import { api } from "../../services/endpoints.js";
import { el, ICONOS } from "../../utils/dom.js";
import { dinero, dineroConSigno, fechaCorta, mesActual, etiquetaMes } from "../../utils/formato.js";
import { estadoError, estadoVacio, toast } from "../../utils/ui.js";
import { crearDona, crearLinea, destruir } from "./graficos.js";

/** Icono de figura para la celda de concepto. */
function iconoMovimiento(tipo) {
  const icono = el("i", { class: `figura-icono ${tipo}`, "aria-hidden": "true" });
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("viewBox", "0 0 24 24");
  svg.setAttribute("fill", "none");
  svg.setAttribute("stroke", "currentColor");
  svg.setAttribute("stroke-width", "2");
  svg.setAttribute("stroke-linecap", "round");
  svg.setAttribute("aria-hidden", "true");
  svg.innerHTML = tipo === "ingreso"
    ? ICONOS.flechaArriba
    : ICONOS.flechaAbajo;
  icono.append(svg);
  return icono;
}

function filaReciente(movimiento) {
  return el("tr", {},
    el("td", { class: "celda-fecha" },
      el("div", { class: "celda-figura" },
        iconoMovimiento(movimiento.tipo),
        el("strong", { class: "celda-concepto", title: movimiento.notas || "" },
          movimiento.descripcion || "Movimiento"),
      )),
    el("td", {},
      el("small", { class: "badge-categoria" },
        el("i", { class: "punto-categoria", style: { backgroundColor: movimiento.categoria.color }, "aria-hidden": "true" }),
        movimiento.categoria.nombre)),
    el("td", { class: "celda-fecha" },
      el("time", { datetime: movimiento.fecha }, fechaCorta(movimiento.fecha))),
    el("td", { class: `celda-monto derecha ${movimiento.tipo}` },
      el("data", { value: String(movimiento.monto), class: "monto-valor" },
        dineroConSigno(movimiento.monto, movimiento.moneda || undefined))),
  );
}

const PATRON_MES = /^\d{4}-(0[1-9]|1[0-2])$/;

function mesValidoOMesActual(valor) {
  return PATRON_MES.test(valor || "") ? valor : mesActual();
}

export async function montarPanel(main) {
  const inputMes = document.getElementById("input-mes");
  // No pisar el mes elegido por el usuario al volver a la vista; solo
  // inicializar si está vacío o es inválido.
  inputMes.value = mesValidoOMesActual(inputMes.value);

  const contenedores = {
    ingresos: main.querySelector("#kpi-ingresos"),
    gastos: main.querySelector("#kpi-gastos"),
    balance: main.querySelector("#kpi-balance"),
    ahorro: main.querySelector("#kpi-ahorro"),
    prediccion: main.querySelector("#kpi-prediccion-valor"),
    banner: main.querySelector("#banner-anomalias"),
    bannerMensaje: main.querySelector("#banner-mensaje"),
    donaLeyenda: main.querySelector("#dona-leyenda"),
    recientes: main.querySelector("#recientes-contenido"),
  };

  let graficoDona = null;
  let graficoLinea = null;

  async function cargar(mes) {
    try {
      const panel = await api.panel.completo(mes);
      // Totales ya convertidos por el backend; la moneda la indica la respuesta.
      const moneda = panel.moneda || panel.resumen.moneda || undefined;

      /* ------------------------------- KPIs ------------------------------ */
      contenedores.ingresos.textContent = dinero(panel.resumen.total_ingresos, moneda);
      contenedores.gastos.textContent = dinero(panel.resumen.total_gastos, moneda);
      contenedores.balance.textContent = dinero(panel.resumen.balance, moneda);

      const porcentajeAhorro = panel.resumen.total_ingresos > 0
        ? Math.round(Number(panel.resumen.balance) / Number(panel.resumen.total_ingresos) * 100)
        : 0;
      if (panel.resumen.total_ingresos > 0) {
        contenedores.ahorro.hidden = false;
        contenedores.ahorro.textContent = `Ahorro: ${porcentajeAhorro}%`;
      } else {
        contenedores.ahorro.hidden = true;
      }

      if (panel.prediccion.disponible) {
        contenedores.prediccion.textContent = dinero(panel.prediccion.valor_predicho, moneda);
      } else {
        contenedores.prediccion.textContent = "—";
        main.querySelector("#kpi-prediccion").title = panel.prediccion.mensaje || "";
      }

      /* ------------------------ Banner de anomalías ---------------------- */
      const anomalias = panel.anomalias;
      if (anomalias.disponible && anomalias.items?.length) {
        contenedores.banner.hidden = false;
        const primera = anomalias.items[0];
        contenedores.bannerMensaje.textContent = primera
          ? `${primera.tipo === "gasto" ? "Gasto" : "Ingreso"} atípico en ${primera.categoria}` +
            ` (${dinero(primera.monto, moneda)}; puntuación ${primera.puntuacion.toFixed(2)})`
          : anomalias.mensaje || "";
      } else {
        contenedores.banner.hidden = true;
      }

      /* ------------------------------ Gráficos ---------------------------- */
      graficoDona?.destroy();
      graficoDona = null;
      graficoLinea?.destroy();
      graficoLinea = null;

      const dona = panel.gastos_por_categoria.filter((c) => Number(c.total) > 0);
      const canvasDona = main.querySelector("#grafico-dona");
      const envolturaDona = main.querySelector("#dona-envoltura");
      // El canvas vive en el template: nunca se elimina del DOM, solo se
      // oculta. Eliminar el canvas (replaceChildren) dejaba
      // querySelector("#grafico-dona") en null en la siguiente carga y
      // new Chart(null) lanzaba el "Error al cargar el panel".
      envolturaDona.querySelector(".estado-vacio-dona")?.remove();

      if (dona.length) {
        envolturaDona.hidden = false;
        if (canvasDona) {
          canvasDona.hidden = false;
          graficoDona = crearDona(canvasDona, dona, (v) => dinero(v, moneda));
        }
        contenedores.donaLeyenda.replaceChildren(...dona.map((c) =>
          el("li", { class: "leyenda-item" },
            el("i", { class: "leyenda-punto", style: { backgroundColor: c.color }, "aria-hidden": "true" }),
            el("small", { class: "leyenda-nombre" }, c.nombre),
            el("data", { class: "leyenda-porcentaje", value: String(Math.round(c.porcentaje)) }, `${Math.round(c.porcentaje)}%`)),
        ));
      } else {
        contenedores.donaLeyenda.replaceChildren();
        if (canvasDona) canvasDona.hidden = true;
        const vacio = estadoVacioSinFormato("Aún no tienes gastos este mes. ¡Registra el primero!");
        vacio.classList.add("estado-vacio-dona");
        envolturaDona.append(vacio);
        envolturaDona.hidden = false;
      }

      const canvasLinea = main.querySelector("#grafico-linea");
      if (canvasLinea) {
        graficoLinea = crearLinea(canvasLinea, panel.evolucion, (v) => dinero(v, moneda));
      }

      /* ------------------------ Movimientos recientes ---------------------- */
      const recientes = await api.movimientos.listar({ pagina: 1, por_pagina: 5 });
      if (!recientes.items.length) {
        contenedores.recientes.replaceChildren(
          el("div", { class: "estado" },
            el("p", {}, "No hay movimientos todavía."),
            el("button", {
              class: "btn btn-primario", type: "button",
              onclick: () => document.getElementById("btn-nuevo-movimiento").click(),
            }, "Registrar el primero")),
        );
      } else {
        const tabla = el("table", { class: "tabla-datos" },
          el("caption", { class: "solo-lectores" }, "Últimos movimientos"),
          el("thead", {}, el("tr", {},
            el("th", { scope: "col" }, "Concepto"),
            el("th", { scope: "col" }, "Categoría"),
            el("th", { scope: "col" }, "Fecha"),
            el("th", { scope: "col", class: "derecha" }, "Monto"))),
          el("tbody", {}, recientes.items.map(filaReciente)));
        contenedores.recientes.replaceChildren(tabla);
      }
    } catch (error) {
      estadoError(contenedores.recientes, `No se pudo cargar el panel: ${error.message}`,
        el("button", { class: "btn btn-secundario", type: "button", onclick: () => cargar(mesActual()) }, "Reintentar"));
      toast("Error al cargar el panel", "error");
    }
  }

  // inputMes vive en el shell (fuera de main): el listener debe
  // removerse al salir o se acumula uno por cada visita a /panel y
  // dispara N cargas + N toasts "Error al cargar el panel".
  const alCambiarMes = () => {
    const mes = mesValidoOMesActual(inputMes.value);
    inputMes.value = mes;
    cargar(mes);
  };
  inputMes.addEventListener("change", alCambiarMes);

  // KPI de predicción ya es un <a href="#/analisis"> en la plantilla:
  // la navegación es nativa, sin listener clicable sobre article.

  await cargar(mesValidoOMesActual(inputMes.value));

  // Limpieza al abandonar la vista
  return () => {
    inputMes.removeEventListener("change", alCambiarMes);
    graficoDona?.destroy();
    graficoLinea?.destroy();
    graficoDona = null;
    graficoLinea = null;
  };
}

/** Estado vacío sin clase .estado duplicada (para el envoltorio de la dona). */
function estadoVacioSinFormato(mensaje) {
  const div = el("div", { class: "estado" }, el("p", {}, mensaje));
  return div;
}
