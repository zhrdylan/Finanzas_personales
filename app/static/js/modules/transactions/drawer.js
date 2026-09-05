/**
 * Drawer lateral (slide-over) para crear/editar movimientos.
 * Reproduce el "NuevoMovimientoDrawer" del prototipo en HTML/CSS/JS puro:
 * panel anclado a la derecha, cabecera fija y foco atrapado.
 */

import { api } from "../../services/endpoints.js";
import { monedaActual } from "../../core/sesion.js";
import { el } from "../../utils/dom.js";
import { hoyISO } from "../../utils/formato.js";
import { confirmarAccion } from "../../utils/modal.js";
import { toast } from "../../utils/ui.js";

/**
 * Abre el drawer con el formulario de movimiento.
 * @param {object|null} movimiento  Movimiento a editar (o null para crear).
 * @param {Function} alGuardar      Callback tras guardar (refresca la vista).
 * @returns {Function} función cerrar().
 */
export function abrirDrawerMovimiento(movimiento, alGuardar) {
  const focoAnterior = document.activeElement;

  /* ------------------------------ Esqueleto ------------------------------ */
  const titulo = el("h2", {}, movimiento ? "Editar movimiento" : "Nuevo movimiento");
  const btnCerrar = el("button", {
    class: "btn-cerrar-modal", type: "button", "aria-label": "Cerrar panel",
  }, "✕");

  const form = el("form", { novalidate: true, class: "drawer-cuerpo" });
  const tituloId = movimiento ? "drawer-titulo-editar" : "drawer-titulo-nuevo";
  titulo.setAttribute("id", tituloId);
  const panel = el("div", { class: "drawer" },
    el("div", { class: "drawer-cabecera" }, titulo, btnCerrar),
    form);

  const dialogo = el("dialog", { class: "drawer-dialog", "aria-labelledby": tituloId }, panel);
  document.body.append(dialogo);
  document.body.classList.add("sin-scroll");
  if (typeof dialogo.showModal === "function") dialogo.showModal();
  else dialogo.setAttribute("open", "");

  function cerrar() {
    try { if (dialogo.open) dialogo.close(); } catch { /* fallback sin showModal */ }
    dialogo.remove();
    document.body.classList.remove("sin-scroll");
    if (focoAnterior instanceof HTMLElement) focoAnterior.focus();
  }
  btnCerrar.addEventListener("click", cerrar);
  dialogo.addEventListener("cancel", (e) => { e.preventDefault(); cerrar(); });
  dialogo.addEventListener("click", (e) => { if (e.target === dialogo) cerrar(); });

  /* ------------------------------- Campos -------------------------------- */
  let tipo = movimiento?.tipo || "gasto";
  let categorias = [];

  const conmutador = el("fieldset", { class: "drawer-tipo" },
    el("legend", { class: "solo-lectores" }, "Tipo de movimiento"),
    el("button", { type: "button", "data-tipo": "ingreso", "aria-pressed": "false" }, "Ingreso"),
    el("button", { type: "button", "data-tipo": "gasto", "aria-pressed": "false" }, "Gasto"));

  // Monto hero (estilo Imagen 1: tarjeta con $ grande y valor centrado)
  const inputMonto = el("input", {
    id: "drawer-monto", type: "number", step: "any", min: "0",
    inputmode: "decimal", required: true, placeholder: "0.00",
    value: movimiento ? String(movimiento.monto) : "",
  });
  const campoMonto = el("div", { class: "drawer-monto-hero" },
    el("label", { for: "drawer-monto", class: "drawer-etiqueta" }, "Monto"),
    el("div", { class: "campo-monto-hero" },
      el("i", { class: "simbolo", "aria-hidden": "true" }, "$"), inputMonto));

  // Concepto = descripcion (columna existente, max 255)
  const inputConcepto = el("input", {
    id: "drawer-concepto", type: "text", required: true, maxlength: "255",
    placeholder: "Ej. Supermercado, Nómina, Gasolina…",
    value: movimiento?.descripcion || "",
  });
  const campoConcepto = el("div", { class: "campo" },
    el("label", { for: "drawer-concepto", class: "drawer-etiqueta" }, "Concepto"),
    inputConcepto);

  const inputFecha = el("input", {
    id: "drawer-fecha", type: "date", required: true,
    value: movimiento?.fecha || hoyISO(),
  });
  const campoFecha = el("div", { class: "campo" },
    el("label", { for: "drawer-fecha", class: "drawer-etiqueta" }, "Fecha"), inputFecha);

  const selectCategoria = el("select", {
    id: "drawer-categoria", required: true,
  });
  const campoCategoria = el("div", { class: "campo" },
    el("label", { for: "drawer-categoria", class: "drawer-etiqueta" }, "Categoría"),
    selectCategoria);

  // Método de pago debajo de categoría (requerido por la API)
  const selectMetodo = el("select", { id: "drawer-metodo" },
    el("option", { value: "efectivo" }, "Efectivo"),
    el("option", { value: "tarjeta" }, "Tarjeta"),
    el("option", { value: "transferencia" }, "Transferencia"),
    el("option", { value: "otro" }, "Otro"));
  selectMetodo.value = movimiento?.metodo_pago || "efectivo";
  const campoMetodo = el("div", { class: "campo" },
    el("label", { for: "drawer-metodo", class: "drawer-etiqueta" }, "Método de pago"),
    selectMetodo);

  // Moneda original del registro (no se convierte al guardar)
  const selectMoneda = el("select", { id: "drawer-moneda" },
    el("option", { value: "COP" }, "COP — Peso colombiano"),
    el("option", { value: "USD" }, "USD — Dólar estadounidense"),
    el("option", { value: "EUR" }, "EUR — Euro"));
  selectMoneda.value = movimiento?.moneda || monedaActual();
  const campoMoneda = el("div", { class: "campo" },
    el("label", { for: "drawer-moneda", class: "drawer-etiqueta" }, "Moneda"),
    selectMoneda);

  // Notas adicionales opcionales (columna independiente `notas`, max 500)
  const inputNotas = el("textarea", {
    id: "drawer-notas", rows: "3", maxlength: "500",
    placeholder: "Añade un detalle o nota adicional…",
  }, movimiento?.notas || "");
  const campoNotas = el("div", { class: "campo" },
    el("label", { for: "drawer-notas", class: "drawer-etiqueta" }, "Descripción / Notas"),
    inputNotas);

  const alerta = el("p", { class: "alerta alerta-error", role: "alert", hidden: true });

  const btnCancelar = el("button", { class: "btn btn-fantasma", type: "button" }, "Cancelar");
  const btnGuardar = el("button", { class: "btn btn-primario", type: "submit" },
    movimiento ? "Guardar cambios" : "Guardar");

  form.append(
    conmutador, campoMonto, campoConcepto,
    campoFecha, campoCategoria, campoMetodo, campoMoneda, campoNotas, alerta,
    el("div", { class: "drawer-pie" }, btnCancelar, btnGuardar),
  );
  btnCancelar.addEventListener("click", cerrar);

  /* ------------------------------- Lógica -------------------------------- */
  function pintarTipo() {
    conmutador.querySelectorAll("button").forEach((btn) => {
      btn.setAttribute("aria-pressed", String(btn.dataset.tipo === tipo));
    });
    const opcionesFiltradas = categorias.filter((c) => c.tipo === tipo);
    selectCategoria.replaceChildren(
      el("option", { value: "" }, "Selecciona una categoría…"),
      ...opcionesFiltradas.map((c) => el("option", { value: String(c.id) }, c.nombre)),
    );
    if (movimiento && movimiento.categoria?.tipo === tipo) {
      selectCategoria.value = String(movimiento.categoria.id);
    } else if (opcionesFiltradas.length) {
      selectCategoria.value = String(opcionesFiltradas[0].id);
    } else {
      selectCategoria.value = "";
    }
  }

  conmutador.addEventListener("click", (e) => {
    const btn = e.target.closest("button[data-tipo]");
    if (!btn) return;
    tipo = btn.dataset.tipo;
    pintarTipo();
  });

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    alerta.hidden = true;

    const monto = Number(inputMonto.value);
    if (!(monto > 0)) {
      alerta.textContent = "Por favor introduce un monto válido mayor a 0";
      alerta.hidden = false;
      return;
    }
    const concepto = inputConcepto.value.trim();
    if (!concepto) {
      alerta.textContent = "Escribe el concepto del movimiento";
      alerta.hidden = false;
      inputConcepto.focus();
      return;
    }
    if (!inputFecha.value) {
      alerta.textContent = "Elige la fecha del movimiento";
      alerta.hidden = false;
      inputFecha.focus();
      return;
    }
    if (!selectCategoria.value) {
      alerta.textContent = tipo === "gasto"
        ? "No tienes categorías de gasto. Crea una primero."
        : "No tienes categorías de ingreso. Crea una primero.";
      alerta.hidden = false;
      return;
    }

    // descripcion = concepto; notas = columna independiente (null si vacía)
    const notasTexto = inputNotas.value.trim();
    const datos = {
      tipo,
      monto: monto.toFixed(2),
      moneda: selectMoneda.value,
      categoria_id: Number(selectCategoria.value),
      fecha: inputFecha.value,
      descripcion: concepto,
      notas: notasTexto || null,
      metodo_pago: selectMetodo.value,
    };

    btnGuardar.disabled = true;
    try {
      if (movimiento) {
        await api.movimientos.actualizar(movimiento.id, datos);
        toast("Movimiento actualizado", "exito");
      } else {
        await api.movimientos.crear(datos);
        toast("Movimiento registrado", "exito");
      }
      cerrar();
      // Esperar el refresco de la vista para que el movimiento aparezca
      // sin recargar la página.
      await alGuardar?.();
    } catch (error) {
      alerta.textContent = error.message;
      alerta.hidden = false;
    } finally {
      btnGuardar.disabled = false;
    }
  });

  /* Carga de categorías y foco inicial */
  api.categorias.listar()
    .then((lista) => {
      categorias = lista;
      pintarTipo();
      inputMonto.focus();
    })
    .catch((error) => {
      alerta.textContent = `No se pudieron cargar las categorías: ${error.message}`;
      alerta.hidden = false;
    });

  return cerrar;
}

/** Confirmación y eliminación de un movimiento. */
export async function eliminarMovimiento(movimiento, alEliminar) {
  const ok = await confirmarAccion({
    titulo: "Eliminar movimiento",
    mensaje: `¿Eliminar el movimiento "${movimiento.descripcion || "sin concepto"}" de ${movimiento.fecha}?`,
  });
  if (!ok) return;
  try {
    await api.movimientos.eliminar(movimiento.id);
    toast("Movimiento eliminado", "exito");
    await alEliminar?.();
  } catch (error) {
    toast(error.message, "error");
  }
}
