/**
 * Vista Movimientos: filtros (búsqueda, fechas, categoría, método, tipo),
 * tabla con orden por fecha/monto, paginación y acciones editar/eliminar.
 */

import { api } from "../../services/endpoints.js";
import { el, ICONOS } from "../../utils/dom.js";
import { dineroConSigno, fechaCorta } from "../../utils/formato.js";
import { antiRebote, estadoCargando, estadoError, estadoVacio } from "../../utils/ui.js";
import { abrirDrawerMovimiento, eliminarMovimiento } from "./drawer.js";

function accionesFila(movimiento, alTerminar) {
  const btnEditar = el("button", {
    class: "btn-accion", type: "button", title: "Editar movimiento",
    "aria-label": "Editar movimiento",
  });
  btnEditar.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${ICONOS.editar}</svg>`;
  btnEditar.addEventListener("click", () => abrirDrawerMovimiento(movimiento, alTerminar));

  const btnEliminar = el("button", {
    class: "btn-accion peligro", type: "button", title: "Eliminar movimiento",
    "aria-label": "Eliminar movimiento",
  });
  btnEliminar.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${ICONOS.papelera}</svg>`;
  btnEliminar.addEventListener("click", () => eliminarMovimiento(movimiento, alTerminar));

  return el("div", { class: "acciones" }, btnEditar, btnEliminar);
}

export async function montarMovimientos(main) {
  const estado = {
    q: "", desde: "", hasta: "", categoria: "", metodo: "", moneda: "", tipo: "",
    orden: "fecha", direccion: "desc", pagina: 1,
  };

  const contTabla = main.querySelector("#tabla-contenido");
  const contPaginacion = main.querySelector("#paginacion");
  const contador = main.querySelector("#tabla-contador");
  const neto = main.querySelector("#tabla-neto");
  const btnLimpiar = main.querySelector("#btn-limpiar-filtros");
  const inputQ = main.querySelector("#filtro-q");
  const inputDesde = main.querySelector("#filtro-desde");
  const inputHasta = main.querySelector("#filtro-hasta");
  const selectCategoria = main.querySelector("#filtro-categoria");
  const selectMetodo = main.querySelector("#filtro-metodo");
  const selectMoneda = main.querySelector("#filtro-moneda");

  // Sin rango por defecto: se muestran todos los movimientos hasta que
  // el usuario aplique un filtro. Así el botón "limpiar filtros" (X) solo
  // aparece cuando hay al menos un filtro activo (ver cargar()).
  inputDesde.value = "";
  inputHasta.value = "";
  estado.desde = "";
  estado.hasta = "";
  btnLimpiar.hidden = true;

  /* ------------------------- Carga de categorías ------------------------- */
  api.categorias.listar()
    .then((categorias) => {
      selectCategoria.append(...categorias.map((c) =>
        el("option", { value: String(c.id) }, c.nombre)));
    })
    .catch(() => { /* los filtros funcionan sin categorías */ });

  /* ------------------------------ Renderizado ---------------------------- */
  function ordenHTML(campo, etiqueta) {
    const activo = estado.orden === campo;
    const flecha = activo ? (estado.direccion === "asc" ? " ↑" : " ↓") : "";
    return `${etiqueta}${flecha}`;
  }

  function fila(movimiento, alTerminar) {
    const esIngreso = movimiento.tipo === "ingreso";
    const monedaOrigen = movimiento.moneda || "COP";
    return el("tr", {},
      el("td", { class: "celda-fecha" },
        el("time", { datetime: movimiento.fecha }, fechaCorta(movimiento.fecha))),
      el("td", { class: "celda-concepto", title: movimiento.notas || "" },
        el("strong", { class: "celda-concepto-texto" }, movimiento.descripcion || "Movimiento"),
        el("small", { class: "celda-nota" }, `${monedaOrigen} · ${movimiento.metodo_pago}`)),
      el("td", {},
        el("small", { class: "badge-categoria" },
          el("i", { class: "punto-categoria", style: { backgroundColor: movimiento.categoria.color }, "aria-hidden": "true" }),
          movimiento.categoria.nombre)),
      el("td", { class: "centro" },
        el("data", { class: `etiqueta etiqueta-${movimiento.tipo}`, value: movimiento.tipo },
          esIngreso ? "Ingreso" : "Gasto")),
      el("td", { class: `celda-monto derecha ${movimiento.tipo}` },
        el("data", { value: `${movimiento.monto}`, class: "monto-valor" },
          dineroConSigno(movimiento.monto, monedaOrigen))),
      el("td", { class: "centro celda-acciones" }, accionesFila(movimiento, alTerminar)),
    );
  }

  async function cargar() {
    estadoCargando(contTabla);
    try {
      const params = {
        pagina: estado.pagina, por_pagina: 20,
        tipo: estado.tipo, categoria_id: estado.categoria,
        metodo_pago: estado.metodo, moneda: estado.moneda,
        fecha_desde: estado.desde,
        fecha_hasta: estado.hasta, q: estado.q,
        orden: estado.orden, direccion: estado.direccion,
      };
      const pagina = await api.movimientos.listar(params);

      // El orden lo aplica el backend (ORDER BY global, correcto con
      // paginación); aquí solo se copian los items de la página.
      const items = [...pagina.items];

      contador.replaceChildren();
      contador.append("Mostrando ", el("strong", {}, String(items.length)),
        ` de ${pagina.total} movimientos`);

      // El neto solo tiene sentido en una única moneda (los montos
      // originales no se suman entre monedas distintas).
      const monedasVistas = new Set(items.map((m) => m.moneda || "COP"));
      if (monedasVistas.size <= 1) {
        const monedaNeta = items[0]?.moneda || "COP";
        const netoValor = items.reduce(
          (acc, m) => acc + Number(m.monto) * (m.tipo === "ingreso" ? 1 : -1), 0);
        neto.textContent = `Neto filtrado: ${dineroConSigno(netoValor, monedaNeta)}`;
        neto.className = `tabla-neto ${netoValor >= 0 ? "positivo" : "negativo"}`;
      } else {
        neto.textContent = "Neto filtrado: — (multi-moneda)";
        neto.title = "Los montos originales están en distintas monedas y no se suman";
        neto.className = "tabla-neto";
      }

      btnLimpiar.hidden = !(estado.q || estado.tipo || estado.categoria ||
        estado.metodo || estado.moneda || estado.desde || estado.hasta);

      if (!items.length) {
        estadoVacio(contTabla, "No se encontraron movimientos",
          el("button", {
            class: "btn btn-primario", type: "button",
            onclick: () => document.getElementById("btn-nuevo-movimiento").click(),
          }, "Registrar nuevo movimiento"));
        contPaginacion.replaceChildren();
        return;
      }

      const alTerminar = async () => { await cargar(); };
      contTabla.replaceChildren(el("table", { class: "tabla-datos" },
        el("caption", { class: "solo-lectores" }, "Listado de movimientos filtrados"),
        el("thead", {}, el("tr", {},
          el("th", { scope: "col", class: "enlace-orden" },
            el("button", {
              type: "button", class: "btn-orden",
              title: "Ordenar por fecha",
              "aria-label": `Ordenar por fecha (${estado.direccion === "asc" ? "ascendente" : "descendente"})`,
              onclick: () => alternarOrden("fecha"),
            }, ordenHTML("fecha", "Fecha"))),
          el("th", { scope: "col" }, "Descripción"),
          el("th", { scope: "col" }, "Categoría"),
          el("th", { scope: "col", class: "centro" }, "Tipo"),
          el("th", { scope: "col", class: "derecha" },
            el("button", {
              type: "button", class: "btn-orden",
              title: "Ordenar por monto",
              "aria-label": `Ordenar por monto (${estado.direccion === "asc" ? "ascendente" : "descendente"})`,
              onclick: () => alternarOrden("monto"),
            }, ordenHTML("monto", "Monto"))),
          el("th", { scope: "col", class: "centro" }, "Acciones"))),
        el("tbody", {}, items.map((m) => fila(m, alTerminar)))));

      /* ------------------------------ Paginación ---------------------------- */
      function botonPagina(texto, pagina, actual = false, deshabilitado = false) {
        return el("button", {
          type: "button",
          "aria-current": actual ? "page" : null,
          disabled: deshabilitado || undefined,
          onclick: () => { estado.pagina = pagina; cargar(); },
        }, texto);
      }
      const botones = [
        botonPagina("‹", pagina.pagina - 1, false, pagina.pagina <= 1),
      ];
      for (let p = 1; p <= pagina.total_paginas; p += 1) {
        if (pagina.total_paginas > 7 && Math.abs(p - pagina.pagina) > 2 &&
            p !== 1 && p !== pagina.total_paginas) {
          if (botones.at(-1)?.textContent !== "…") botones.push(botonPagina("…", p, false, true));
          continue;
        }
        botones.push(botonPagina(String(p), p, p === pagina.pagina));
      }
      botones.push(botonPagina("›", pagina.pagina + 1, false, pagina.pagina >= pagina.total_paginas));
      contPaginacion.replaceChildren(
        el("ul", { class: "paginacion-lista" },
          ...botones.map((b) => el("li", {}, b))));
    } catch (error) {
      estadoError(contTabla, `No se pudieron cargar los movimientos: ${error.message}`,
        el("button", { class: "btn btn-secundario", type: "button", onclick: () => cargar() }, "Reintentar"));
    }
  }

  function alternarOrden(campo) {
    if (estado.orden === campo) {
      estado.direccion = estado.direccion === "asc" ? "desc" : "asc";
    } else {
      estado.orden = campo;
      estado.direccion = "desc";
    }
    // Al cambiar el orden global se vuelve a la primera página.
    estado.pagina = 1;
    cargar();
  }

  /* -------------------------------- Eventos ------------------------------- */
  inputQ.addEventListener("input", antiRebote(() => {
    estado.q = inputQ.value.trim(); estado.pagina = 1; cargar();
  }));
  inputDesde.addEventListener("change", () => { estado.desde = inputDesde.value; estado.pagina = 1; cargar(); });
  inputHasta.addEventListener("change", () => { estado.hasta = inputHasta.value; estado.pagina = 1; cargar(); });
  selectCategoria.addEventListener("change", () => { estado.categoria = selectCategoria.value; estado.pagina = 1; cargar(); });
  selectMetodo.addEventListener("change", () => { estado.metodo = selectMetodo.value; estado.pagina = 1; cargar(); });
  if (selectMoneda) {
    selectMoneda.addEventListener("change", () => { estado.moneda = selectMoneda.value; estado.pagina = 1; cargar(); });
  }

  main.querySelectorAll(".conmutador-compacto button").forEach((btn) => {
    btn.addEventListener("click", () => {
      main.querySelectorAll(".conmutador-compacto button").forEach((b) =>
        b.setAttribute("aria-pressed", "false"));
      btn.setAttribute("aria-pressed", "true");
      estado.tipo = btn.dataset.tipo;
      estado.pagina = 1;
      cargar();
    });
  });

  btnLimpiar.addEventListener("click", () => {
    estado.q = ""; estado.desde = ""; estado.hasta = "";
    estado.categoria = ""; estado.metodo = ""; estado.moneda = ""; estado.tipo = "";
    estado.pagina = 1;
    inputQ.value = ""; inputDesde.value = ""; inputHasta.value = "";
    selectCategoria.value = ""; selectMetodo.value = "";
    if (selectMoneda) selectMoneda.value = "";
    main.querySelectorAll(".conmutador-compacto button").forEach((b, i) =>
      b.setAttribute("aria-pressed", String(i === 0)));
    cargar();
  });

  await cargar();
  return null;
}
