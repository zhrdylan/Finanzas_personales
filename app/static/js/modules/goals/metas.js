/**
 * Vista Metas de ahorro: total acumulado, tarjetas con progreso radial,
 * aporte de dinero, creación y edición (datos reales persistidos en MySQL).
 */

import { api } from "../../services/endpoints.js";
import { monedaActual } from "../../core/sesion.js";
import { el, ICONOS } from "../../utils/dom.js";
import { dinero, fechaCorta, hoyISO } from "../../utils/formato.js";
import { abrirModal, confirmarAccion } from "../../utils/modal.js";
import { estadoCargando, estadoVacio, toast } from "../../utils/ui.js";
import { celebrarConConfeti } from "../../utils/confeti.js";
import { UMBRAL_META_CERCANA } from "./constantes.js";

function svgIcono(nombre, clase) {
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("viewBox", "0 0 24 24");
  svg.setAttribute("fill", "none");
  svg.setAttribute("stroke", "currentColor");
  svg.setAttribute("stroke-width", "2");
  svg.setAttribute("stroke-linecap", "round");
  svg.setAttribute("stroke-linejoin", "round");
  svg.setAttribute("aria-hidden", "true");
  svg.innerHTML = ICONOS[nombre] || "";
  if (clase) svg.setAttribute("class", clase);
  return svg;
}

/** Etiqueta de estado según el porcentaje (lógica del prototipo). */
function etiquetaEstado(meta) {
  if (meta.estado === "cumplida") {
    return el("strong", { class: "etiqueta etiqueta-meta-cumplida" }, "¡Alcanzada!");
  }
  if (meta.porcentaje >= UMBRAL_META_CERCANA) {
    return el("em", { class: "etiqueta etiqueta-meta-cercana" }, "Meta cercana");
  }
  if (meta.porcentaje >= 40) {
    return el("em", { class: "etiqueta etiqueta-meta-avance" }, "¡Buen avance!");
  }
  return el("em", { class: "etiqueta etiqueta-meta-activa" }, "En curso");
}

/** Dial radial de progreso (SVG como en el prototipo). */
function dialProgreso(meta) {
  const progreso = Math.min(100, meta.porcentaje);
  const radio = 38;
  const circunferencia = 2 * Math.PI * radio;
  const desplazamiento = circunferencia - (progreso / 100) * circunferencia;
  const cumplida = meta.estado === "cumplida";

  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("viewBox", "0 0 96 96");
  const fondo = document.createElementNS("http://www.w3.org/2000/svg", "circle");
  fondo.setAttribute("cx", "48"); fondo.setAttribute("cy", "48");
  fondo.setAttribute("r", String(radio));
  fondo.setAttribute("fill", "none");
  fondo.setAttribute("stroke", "#f0efff");
  fondo.setAttribute("stroke-width", "8");
  const arco = document.createElementNS("http://www.w3.org/2000/svg", "circle");
  arco.setAttribute("cx", "48"); arco.setAttribute("cy", "48");
  arco.setAttribute("r", String(radio));
  arco.setAttribute("fill", "none");
  arco.setAttribute("stroke", cumplida ? "#55ddac" : "#0053ce");
  arco.setAttribute("stroke-width", "8");
  arco.setAttribute("stroke-linecap", "round");
  arco.setAttribute("stroke-dasharray", String(circunferencia));
  arco.setAttribute("stroke-dashoffset", String(desplazamiento));
  svg.append(fondo, arco);
  svg.setAttribute("aria-hidden", "true");

  return el("div", { class: "meta-dial", role: "img", "aria-label": `${Math.round(progreso)}% ahorrado` }, svg,
    el("output", { class: "meta-dial-valor" }, `${Math.round(progreso)}%`),
    el("progress", { class: "solo-lectores", max: "100", value: String(Math.round(progreso)) }, `${Math.round(progreso)}%`));
}

/** Modal de nueva/editar meta. */
function modalMeta(meta, alGuardar) {
  const form = el("form", { novalidate: true });

  const inputNombre = el("input", {
    id: "meta-nombre",
    type: "text", required: true, maxlength: "100",
    placeholder: "Ej. Viaje a Europa, Computador…",
    value: meta?.nombre || "",
  });
  const inputObjetivo = el("input", {
    id: "meta-objetivo",
    type: "number", step: "any", min: "0", required: true,
    placeholder: "2000000", value: meta ? String(meta.monto_objetivo) : "",
  });
  const inputInicial = el("input", {
    id: "meta-inicial",
    type: "number", step: "any", min: "0", placeholder: "0",
    value: meta ? String(meta.monto_actual) : "",
  });
  const inputFecha = el("input", {
    id: "meta-fecha",
    type: "date", value: meta?.fecha_limite || "",
  });
  const selectMoneda = el("select", { id: "meta-moneda" },
    el("option", { value: "COP" }, "COP — Peso colombiano"),
    el("option", { value: "USD" }, "USD — Dólar estadounidense"),
    el("option", { value: "EUR" }, "EUR — Euro"));
  selectMoneda.value = meta?.moneda || monedaActual();
  const alerta = el("p", { class: "alerta alerta-error", role: "alert", hidden: true });

  const campoNombre = el("div", { class: "campo" },
    el("label", { for: "meta-nombre" }, "Nombre de la meta"), inputNombre);
  const campoObjetivo = el("div", { class: "campo" },
    el("label", { for: "meta-objetivo" }, "Monto objetivo"), inputObjetivo);
  const campoInicial = el("div", { class: "campo" },
    el("label", { for: "meta-inicial" },
      meta ? "Monto ahorrado" : "Monto inicial"),
    inputInicial,
    meta ? null : el("small", { class: "nota" }, "Opcional"));
  const campoFecha = el("div", { class: "campo" },
    el("label", { for: "meta-fecha" }, "Fecha estimada"), inputFecha);
  const campoMoneda = el("div", { class: "campo" },
    el("label", { for: "meta-moneda" }, "Moneda"), selectMoneda);

  // Solo crear usa 2 columnas (objetivo | inicial); editar apila los campos.
  if (meta) {
    form.append(campoNombre, campoObjetivo, campoInicial, campoFecha, campoMoneda, alerta);
  } else {
    form.append(
      campoNombre,
      el("div", { class: "fila-dos" }, campoObjetivo, campoInicial),
      campoFecha,
      campoMoneda,
      alerta,
    );
  }

  abrirModal({
    titulo: el("strong", { class: "modal-titulo-icono" },
      svgIcono("corona"), meta ? "Editar meta de ahorro" : "Nueva meta de ahorro"),
    contenido: form,
    textoPrimario: meta ? "Guardar cambios" : "Crear meta",
    onPrimario: async () => {
      const objetivo = Number(inputObjetivo.value);
      const actual = Number(inputInicial.value || 0);
      if (!(objetivo > 0)) {
        alerta.textContent = "Introduce un monto objetivo válido";
        alerta.hidden = false;
        return false;
      }
      if (actual < 0 || actual > objetivo) {
        alerta.textContent = "El monto ahorrado no puede superar el objetivo ni ser negativo";
        alerta.hidden = false;
        return false;
      }
      const base = {
        nombre: inputNombre.value.trim() || "Nueva meta",
        monto_objetivo: objetivo.toFixed(2),
        moneda: selectMoneda.value,
        fecha_limite: inputFecha.value || null,
      };
      // Crear usa `monto_inicial`, editar usa `monto_actual` (contrato del backend).
      const datos = meta
        ? { ...base, monto_actual: actual.toFixed(2) }
        : { ...base, monto_inicial: actual.toFixed(2) };
      try {
        if (meta) {
          await api.metas.actualizar(meta.id, datos);
          toast("Meta actualizada", "exito");
        } else {
          await api.metas.crear(datos);
          toast("Meta creada", "exito");
        }
        await alGuardar();
        return true;
      } catch (error) {
        alerta.textContent = error.message;
        alerta.hidden = false;
        return false;
      }
    },
  });
}

/** Modal de aporte a una meta. */
function modalAporte(meta, alGuardar) {
  const form = el("form", { novalidate: true });
  const inputMonto = el("input", {
    id: "aporte-monto",
    type: "number", step: "any", min: "0", required: true,
    placeholder: "Ej. 100000",
  });
  const alerta = el("p", { class: "alerta alerta-error", role: "alert", hidden: true });
  form.append(
    el("div", { class: "campo" },
      el("label", { for: "aporte-monto" }, "Monto a depositar"),
      el("div", { class: "campo-monto" },
        el("i", { class: "simbolo", "aria-hidden": "true" }, "$"), inputMonto)),
    alerta,
  );

  abrirModal({
    titulo: el("strong", {}, "Aportar a: ", meta.nombre),
    contenido: form,
    textoPrimario: "Confirmar aporte",
    textoSecundario: "Cancelar",
    onPrimario: async () => {
      const monto = Number(inputMonto.value);
      if (!(monto > 0)) {
        alerta.textContent = "Introduce un monto válido mayor a 0";
        alerta.hidden = false;
        return false;
      }
      try {
        const actualizada = await api.metas.aportar(meta.id, monto.toFixed(2));
        const cumplidaAhora = actualizada.estado === "cumplida" && meta.estado !== "cumplida";
        if (cumplidaAhora) celebrarConConfeti();
        toast(actualizada.estado === "cumplida"
          ? "¡Meta alcanzada! 🎉" : "Aporte registrado", "exito");
        await alGuardar();
        return true;
      } catch (error) {
        alerta.textContent = error.message;
        alerta.hidden = false;
        return false;
      }
    },
  });
}

export async function montarMetas(main) {
  const contenedor = main.querySelector("#metas-contenido");
  const contenedorTotal = main.querySelector("#metas-total");
  const filtro = main.querySelector("#metas-filtro");
  const btnActivas = filtro?.querySelector('[data-muestra="activas"]');
  const btnCumplidas = filtro?.querySelector('[data-muestra="cumplidas"]');
  // Las cumplidas se ocultan por defecto; el filtro permite verlas.
  let mostrarCumplidas = false;

  function pintarFiltro(nActivas, nCumplidas) {
    if (!filtro) return;
    filtro.hidden = nCumplidas === 0 && !mostrarCumplidas;
    if (btnActivas) {
      btnActivas.textContent = `Activas (${nActivas})`;
      btnActivas.setAttribute("aria-pressed", String(!mostrarCumplidas));
    }
    if (btnCumplidas) {
      btnCumplidas.textContent = `Completadas (${nCumplidas})`;
      btnCumplidas.setAttribute("aria-pressed", String(mostrarCumplidas));
    }
  }

  function tarjetaMeta(meta) {
    const tarjeta = el("article", { class: "tarjeta tarjeta-meta" });

    const fechaPie = meta.fecha_limite
      ? el("p", { class: "meta-fecha" },
        svgIcono("calendario"),
        el("time", { datetime: meta.fecha_limite }, fechaCorta(meta.fecha_limite)))
      : el("p", { class: "meta-fecha" },
        svgIcono("calendario"),
        el("small", {}, "Sin fecha límite"));

    tarjeta.append(
      el("header", { class: "meta-cabecera" },
        el("h3", { class: "meta-nombre" }, meta.nombre),
        etiquetaEstado(meta)),
      el("div", { class: "meta-progreso" },
        dialProgreso(meta),
        el("div", { class: "meta-montos" },
          el("div", {},
            el("p", { class: "meta-monto-etiqueta" }, "Ahorrado"),
            el("p", { class: "meta-monto-valor" },
              el("data", { value: String(meta.monto_actual) },
                `${dinero(meta.monto_actual, meta.moneda)} ${meta.moneda || "COP"}`))),
          el("div", {},
            el("p", { class: "meta-monto-etiqueta" }, "Objetivo"),
            el("p", { class: "meta-monto-objetivo" },
              el("data", { value: String(meta.monto_objetivo) },
                `${dinero(meta.monto_objetivo, meta.moneda)} ${meta.moneda || "COP"}`))))),
      el("footer", { class: "meta-pie" },
        fechaPie,
        el("div", { style: { display: "flex", gap: "6px" } },
          el("button", {
            class: "btn btn-sutil btn-aportar", type: "button",
            onclick: () => modalAporte(meta, cargar),
          }, "Aportar"),
          el("button", {
            class: "btn-accion", type: "button", title: "Editar meta",
            "aria-label": `Editar meta ${meta.nombre}`,
            onclick: () => modalMeta(meta, cargar),
          }, svgIcono("editar")),
          el("button", {
            class: "btn-accion peligro", type: "button", title: "Eliminar meta",
            "aria-label": `Eliminar meta ${meta.nombre}`,
            onclick: async () => {
              const ok = await confirmarAccion({
                titulo: "Eliminar meta",
                mensaje: `¿Eliminar la meta "${meta.nombre}"? El ahorro acumulado (${dinero(meta.monto_actual)}) no se registra como movimiento.`,
              });
              if (!ok) return;
              try {
                await api.metas.eliminar(meta.id);
                toast("Meta eliminada", "exito");
                await cargar();
              } catch (error) {
                toast(error.message, "error");
              }
            },
          }, svgIcono("papelera")))),
    );
    return el("li", { class: "meta-item" }, tarjeta);
  }

  async function cargar() {
    estadoCargando(contenedor);
    try {
      const metas = await api.metas.listar();
      const activas = metas.filter((m) => m.estado !== "cumplida");
      const cumplidas = metas.filter((m) => m.estado === "cumplida");

      // El total acumula solo las metas activas (visibles por defecto).
      const total = activas.reduce((acc, m) => acc + Number(m.monto_actual), 0);
      contenedorTotal.textContent = dinero(total);
      pintarFiltro(activas.length, cumplidas.length);

      if (!metas.length) {
        estadoVacio(contenedor, "Aún no tienes metas de ahorro. ¡Define tu primer objetivo!",
          el("button", {
            class: "btn btn-primario", type: "button",
            onclick: () => modalMeta(null, cargar),
          }, "Crear mi primera meta"));
        return;
      }

      const visibles = mostrarCumplidas ? cumplidas : activas;
      if (!visibles.length) {
        estadoVacio(contenedor,
          mostrarCumplidas
            ? "No hay metas completadas."
            : "¡Todas tus metas están cumplidas! 🎉",
          el("button", {
            class: "btn btn-secundario", type: "button",
            onclick: () => { mostrarCumplidas = !mostrarCumplidas; cargar(); },
          }, mostrarCumplidas ? "Ver activas" : "Ver completadas"));
        return;
      }

      contenedor.replaceChildren(...visibles.map(tarjetaMeta));
    } catch (error) {
      estadoVacio(contenedor, `No se pudieron cargar las metas: ${error.message}`);
    }
  }

  main.querySelector("#btn-nueva-meta").addEventListener("click", () => modalMeta(null, cargar));

  filtro?.addEventListener("click", (e) => {
    const btn = e.target.closest("button[data-muestra]");
    if (!btn) return;
    mostrarCumplidas = btn.dataset.muestra === "cumplidas";
    cargar();
  });

  await cargar();
  return null;
}
