/**
 * Modales accesibles con <dialog> nativo (Esc, foco atrapado, ::backdrop)
 * y la estética del prototipo: cabecera en #fbf8ff, botón de cierre, pie.
 */

import { el } from "./dom.js";

let contadorModales = 0;

/**
 * Abre un modal.
 *
 * @param {object} opciones
 * @param {string|Node}   opciones.titulo        Encabezado del modal.
 * @param {Node}          opciones.contenido     Nodo del formulario/cuerpo.
 * @param {Function}      [opciones.onPrimario]  Acción del botón primario. Si
 *   devuelve false (o lanza), el modal NO se cierra (p. ej. validación).
 * @param {string}        [opciones.textoPrimario="Guardar"]
 * @param {string}        [opciones.textoSecundario="Cancelar"]
 * @param {boolean}       [opciones.peligro=false]  Estilo de peligro (eliminar).
 * @param {boolean}       [opciones.conPie=true]  Muestra la barra de acciones.
 * @returns {Function} función cerrar().
 */
export function abrirModal({
  titulo, contenido, onPrimario,
  textoPrimario = "Guardar", textoSecundario = "Cancelar",
  peligro = false, conPie = true,
}) {
  const focoAnterior = document.activeElement;
  contadorModales += 1;
  const idTitulo = `modal-titulo-${contadorModales}`;

  const cabecera = el("div", { class: "modal-cabecera" },
    el("h2", { id: idTitulo }, titulo),
    el("button", {
      class: "btn-cerrar-modal", type: "button",
      "aria-label": "Cerrar ventana",
    }, "✕"));

  const modal = el("div", { class: "modal" }, cabecera, contenido);

  const dialogo = el("dialog", {
    class: "modal-dialog", "aria-labelledby": idTitulo,
  }, modal);

  function cerrar() {
    try { if (dialogo.open) dialogo.close(); } catch { /* fallback sin showModal */ }
    dialogo.remove();
    document.body.classList.remove("sin-scroll");
    if (focoAnterior instanceof HTMLElement) focoAnterior.focus();
  }

  cabecera.querySelector(".btn-cerrar-modal").addEventListener("click", cerrar);

  if (conPie) {
    const btnPrimario = el("button", {
      class: peligro ? "btn btn-peligro" : "btn btn-primario",
      type: "button",
    }, textoPrimario);
    const btnSecundario = el("button", { class: "btn btn-fantasma", type: "button" },
      textoSecundario);

    btnSecundario.addEventListener("click", cerrar);
    btnPrimario.addEventListener("click", async () => {
      if (!onPrimario) return cerrar();
      const continuar = await onPrimario();
      if (continuar !== false) cerrar();
    });

    modal.append(el("div", { class: "modal-pie" }, btnSecundario, btnPrimario));
    // Foco inicial: primer campo del formulario (o el botón secundario)
    const primerCampo = modal.querySelector("input, select, textarea");
    setTimeout(() => (primerCampo || btnSecundario).focus(), 0);
  } else {
    const primerCampo = modal.querySelector("input, select, textarea");
    setTimeout(() => (primerCampo || modal).focus(), 0);
  }

  document.body.append(dialogo);
  document.body.classList.add("sin-scroll");
  if (typeof dialogo.showModal === "function") dialogo.showModal();
  else dialogo.setAttribute("open", "");

  // Cierre con Escape nativo y clic en el backdrop del <dialog>.
  dialogo.addEventListener("cancel", (e) => { e.preventDefault(); cerrar(); });
  dialogo.addEventListener("click", (e) => { if (e.target === dialogo) cerrar(); });

  return cerrar;
}

/** Confirmación de eliminar: Promise<boolean>. */
export function confirmarAccion({ titulo, mensaje, textoConfirmar = "Eliminar" }) {
  return new Promise((resolver) => {
    let resuelto = false;
    const contenido = el("div", { class: "modal-cuerpo" },
      el("p", { class: "modal-mensaje" }, mensaje));
    const resolverYCerrar = (valor) => {
      if (resuelto) return;
      resuelto = true;
      resolver(valor);
      return valor;
    };
    abrirModal({
      titulo, contenido, peligro: true, textoPrimario: textoConfirmar,
      textoSecundario: "Cancelar",
      onPrimario: () => { resolverYCerrar(true); return true; },
    });
    // Si se cierra por Esc, fondo o Cancelar, se resuelve "false"
    const observador = new MutationObserver(() => {
      if (!document.body.contains(contenido) && !resuelto) {
        resuelto = true;
        resolver(false);
        observador.disconnect();
      }
    });
    observador.observe(document.body, { childList: true, subtree: true });
  });
}
