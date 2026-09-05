/**
 * Vista Categorías: pestañas gasto/ingreso, tarjetas con menú contextual y
 * modal de creación/edición con paleta de colores (diseño del prototipo).
 */

import { api } from "../../services/endpoints.js";
import { el, ICONOS } from "../../utils/dom.js";
import { abrirModal, confirmarAccion } from "../../utils/modal.js";
import { estadoCargando, estadoVacio, toast } from "../../utils/ui.js";
import { PALETA_COLORES } from "../../core/config.js";

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

/** Modal de crear/editar categoría con paleta de colores. */
function modalCategoria(categoria, tipoActivo, alGuardar) {
  let tipo = categoria?.tipo || tipoActivo;
  let color = categoria?.color || PALETA_COLORES[0];

  const form = el("form", { novalidate: true });

  const conmutador = el("fieldset", { class: "conmutador" },
    el("legend", { class: "solo-lectores" }, "Tipo de categoría"),
    el("button", { type: "button", "data-tipo": "gasto", "aria-pressed": "false" }, "Gasto"),
    el("button", { type: "button", "data-tipo": "ingreso", "aria-pressed": "false" }, "Ingreso"));

  const inputNombre = el("input", {
    id: "modal-cat-nombre",
    type: "text", required: true, maxlength: "50", value: categoria?.nombre || "",
    placeholder: "Ej. Restaurantes, Gimnasio, Freelance…",
  });
  const campoNombre = el("div", { class: "campo" },
    el("label", { for: "modal-cat-nombre" }, "Nombre de categoría"), inputNombre);

  const paleta = el("div", { class: "paleta-colores", role: "group", "aria-label": "Color identificador" });

  function pintarPaleta() {
    paleta.replaceChildren(...PALETA_COLORES.map((c) => el("button", {
      type: "button", class: "color-opcion", style: { backgroundColor: c },
      "aria-pressed": String(c === color), "aria-label": `Color ${c}`,
      onclick: () => { color = c; pintarPaleta(); },
    }, c === color ? svgIcono("chulo") : "")));
  }

  function pintarTipo() {
    conmutador.querySelectorAll("button").forEach((btn) => {
      btn.setAttribute("aria-pressed", String(btn.dataset.tipo === tipo));
    });
  }

  conmutador.addEventListener("click", (e) => {
    const btn = e.target.closest("button[data-tipo]");
    if (!btn) return;
    tipo = btn.dataset.tipo;
    pintarTipo();
  });

  pintarPaleta();
  pintarTipo();

  const alerta = el("p", { class: "alerta alerta-error", role: "alert", hidden: true });
  form.append(conmutador, campoNombre,
    el("fieldset", { class: "campo" },
      el("legend", {}, "Color identificador"), paleta), alerta);

  const cerrar = abrirModal({
    titulo: categoria ? "Editar categoría" : "Nueva categoría",
    contenido: form,
    textoPrimario: "Guardar",
    onPrimario: async () => {
      const nombre = inputNombre.value.trim();
      if (!nombre) { inputNombre.focus(); return false; }
      try {
        if (categoria) {
          await api.categorias.actualizar(categoria.id, { nombre, tipo, color });
          toast("Categoría actualizada", "exito");
        } else {
          await api.categorias.crear({ nombre, tipo, color });
          toast("Categoría creada", "exito");
        }
        // Esperar el refresco antes de cerrar el modal para que la
        // tarjeta aparezca sin necesidad de recargar la página. Se pasa
        // el tipo guardado para que la vista pueda cambiar de pestaña.
        await alGuardar(tipo);
        return true;
      } catch (error) {
        alerta.textContent = error.message;
        alerta.hidden = false;
        return false;
      }
    },
  });
  return cerrar;
}

export async function montarCategorias(main) {
  let tipoActivo = "gasto";
  const contenedor = main.querySelector("#categorias-contenido");

  function pintarTabs() {
    main.querySelectorAll(".pestanas button").forEach((btn) =>
      btn.setAttribute("aria-selected", String(btn.dataset.tipo === tipoActivo)));
  }

  // Refresco tras crear/editar: si el tipo guardado difiere de la
  // pestaña activa, cambia automáticamente a esa pestaña (decisión del
  // usuario) y luego recarga. Devuelve una promesa para que el modal
  // pueda esperarla (await) antes de cerrarse.
  async function recargar(tipoGuardado) {
    if (tipoGuardado && tipoGuardado !== tipoActivo) {
      tipoActivo = tipoGuardado;
      pintarTabs();
    }
    await cargar();
  }

  async function cargar() {
    estadoCargando(contenedor);
    try {
      const categorias = await api.categorias.listar();
      const filtradas = categorias.filter((c) => c.tipo === tipoActivo);

      if (!filtradas.length) {
        estadoVacio(contenedor,
          `No tienes categorías de ${tipoActivo}. Crea la primera con el botón «Nueva categoría».`);
        return;
      }

      contenedor.replaceChildren(...filtradas.map((categoria) => {
        const btnMenu = el("button", {
          class: "btn-accion", type: "button", "aria-label": `Opciones de ${categoria.nombre}`,
          "aria-haspopup": "true", "aria-expanded": "false",
        });
        btnMenu.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">${ICONOS.vertical}</svg>`;

        const opciones = el("div", { class: "menu-opciones", hidden: true },
          el("button", {
            type: "button", class: "btn-item-menu",
            onclick: () => { opciones.hidden = true; modalCategoria(categoria, tipoActivo, recargar); },
          }, svgIcono("editar"), "Editar"),
          el("button", {
            type: "button", class: "btn-item-menu peligro",
            onclick: async () => {
              opciones.hidden = true;
              const ok = await confirmarAccion({
                titulo: "Eliminar categoría",
                mensaje: `¿Eliminar la categoría "${categoria.nombre}"? Si tiene movimientos asociados no podrá borrarse.`,
              });
              if (!ok) return;
              try {
                await api.categorias.eliminar(categoria.id);
                toast("Categoría eliminada", "exito");
                await cargar();
              } catch (error) {
                toast(error.message, "error");
              }
            },
          }, svgIcono("papelera"), "Eliminar"));

        btnMenu.addEventListener("click", (e) => {
          e.stopPropagation();
          opciones.hidden = !opciones.hidden;
          btnMenu.setAttribute("aria-expanded", String(!opciones.hidden));
        });

        return el("li", { class: "categoria-item" },
          el("article", { class: "tarjeta tarjeta-categoria" },
            el("div", { class: "categoria-identidad" },
              el("i", { class: "categoria-punto", style: { backgroundColor: categoria.color }, "aria-hidden": "true" }),
              el("div", {},
                el("h3", { class: "categoria-nombre" }, categoria.nombre))),
            el("div", { class: "menu-contextual" }, btnMenu, opciones)));
      }));
    } catch (error) {
      estadoVacio(contenedor, `No se pudieron cargar las categorías: ${error.message}`);
    }
  }

  main.querySelectorAll(".pestanas button").forEach((btn) => {
    btn.addEventListener("click", () => {
      tipoActivo = btn.dataset.tipo;
      pintarTabs();
      cargar();
    });
  });

  // Cerrar menús contextuales al hacer clic fuera
  document.addEventListener("click", (e) => {
    if (!e.target.closest(".menu-contextual")) {
      contenedor.querySelectorAll(".menu-opciones").forEach((m) => { m.hidden = true; });
    }
  });

  main.querySelector("#btn-nueva-categoria").addEventListener("click", () => {
    modalCategoria(null, tipoActivo, recargar);
  });

  pintarTabs();
  await cargar();
  return () => {
    // limpieza: nada persistente más allá de listeners ya contenidos
  };
}
