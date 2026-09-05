/**
 * Utilidades de interfaz: toasts, estados (cargando/vacío/error) y helpers.
 */

import { el } from "./dom.js";

/* ------------------------------------------------------------------ *
 * Toasts (avisos no bloqueantes)
 * ------------------------------------------------------------------ */

function zonaToasts() {
  let zona = document.querySelector(".toast-zona");
  if (!zona) {
    zona = el("div", { class: "toast-zona", "aria-live": "polite" });
    document.body.append(zona);
  }
  return zona;
}

/** Muestra un aviso temporal: toast("Guardado", "exito"). */
export function toast(mensaje, tipo = "info", duracion = 4200) {
  const icono = { exito: "✓", error: "!", info: "i" }[tipo] || "i";
  const aviso = el("div", { class: `toast toast-${tipo}`, role: tipo === "error" ? "alert" : "status" },
    el("strong", { "aria-hidden": "true", style: { minWidth: "16px", textAlign: "center" } }, icono),
    el("p", { class: "toast-mensaje" }, mensaje));
  zonaToasts().append(aviso);
  setTimeout(() => aviso.remove(), duracion);
}

/* ------------------------------------------------------------------ *
 * Estados de carga / vacío / error para secciones
 * ------------------------------------------------------------------ */

export function estadoCargando(contenedor, texto = "Cargando…") {
  contenedor.replaceChildren(el("div", { class: "estado", role: "status" },
    el("i", { class: "spinner", "aria-hidden": "true" }),
    el("p", {}, texto)));
}

export function estadoVacio(contenedor, mensaje, accion) {
  const hijos = [el("p", { class: "estado-icono", "aria-hidden": "true" }, "📭"),
    el("p", { class: "estado-titulo" }, mensaje)];
  if (accion) hijos.push(accion);
  const estado = el("div", { class: "estado", role: "status" }, ...hijos);
  // Si el contenedor es una lista (ul/ol), envolver en <li> para HTML válido.
  if (contenedor instanceof HTMLElement && /^(UL|OL)$/.test(contenedor.tagName)) {
    const item = el("li", { class: "estado-item" }, estado);
    contenedor.replaceChildren(item);
  } else {
    contenedor.replaceChildren(estado);
  }
}

export function estadoError(contenedor, mensaje, reintentar) {
  const hijos = [el("p", { class: "estado-icono", "aria-hidden": "true" }, "😵"),
    el("p", { class: "estado-error" }, mensaje)];
  if (reintentar) hijos.push(reintentar);
  contenedor.replaceChildren(el("div", { class: "estado", role: "alert" }, ...hijos));
}

/**
 * Envuelve una acción asíncrona de botón: lo deshabilita y muestra un
 * spinner mientras se ejecuta; restaura el estado al terminar.
 */
export function conCargando(boton, accion) {
  return async (...args) => {
    const textoOriginal = boton.textContent;
    boton.disabled = true;
    boton.textContent = "";
    boton.append(el("i", { class: "spinner", "aria-hidden": "true" }));
    try {
      return await accion(...args);
    } finally {
      boton.disabled = false;
      boton.textContent = textoOriginal;
    }
  };
}

/** Retardo anti-rebote para búsquedas. */
export function antiRebote(fn, ms = 400) {
  let temporizador;
  return (...args) => {
    clearTimeout(temporizador);
    temporizador = setTimeout(() => fn(...args), ms);
  };
}

/** Iniciales para el avatar: "Ana García" -> "AG". */
export function iniciales(nombreCompleto) {
  return (nombreCompleto || "?")
    .split(/\s+/).filter(Boolean).slice(0, 2)
    .map((p) => p[0].toUpperCase()).join("") || "?";
}
