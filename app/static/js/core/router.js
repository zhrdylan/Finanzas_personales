/**
 * Enrutador SPA basado en hash (#/ruta).
 *
 * - Vistas públicas: /login y /registro (pantalla única con pestañas).
 * - Vistas protegidas: /panel, /movimientos, /categorias, /analisis,
 *   /metas, /perfil.
 * - Cada vista clona su <template> y ejecuta un controlador que puede
 *   devolver una función de limpieza (p. ej. destruir gráficos Chart.js).
 */

import { api } from "../services/endpoints.js";
import { estaAutenticado } from "../core/api.js";
import { guardarUsuario, obtenerUsuario, limpiarTokens, obtenerTokens } from "../core/sesion.js";
import { el, pintarIconos, plantilla } from "../utils/dom.js";
import { iniciales } from "../utils/formato.js";
import { toast } from "../utils/ui.js";
import { montarAuth } from "../modules/auth/auth.js";
import { montarPanel } from "../modules/dashboard/panel.js";
import { montarMovimientos } from "../modules/transactions/movimientos.js";
import { montarCategorias } from "../modules/categories/categorias.js";
import { montarAnalisis } from "../modules/analysis/analisis.js";
import { montarMetas } from "../modules/goals/metas.js";
import { montarPerfil } from "../modules/profile/perfil.js";

const VISTAS = {
  "/login":        { plantilla: "tpl-auth", publica: true, titulo: "Iniciar sesión" },
  "/registro":     { plantilla: "tpl-auth", publica: true, titulo: "Crear cuenta" },
  "/panel":        { plantilla: "tpl-panel", titulo: "Resumen financiero", controlador: montarPanel, mes: true },
  "/movimientos":  { plantilla: "tpl-movimientos", titulo: "Movimientos", controlador: montarMovimientos },
  "/categorias":   { plantilla: "tpl-categorias", titulo: "Categorías", controlador: montarCategorias },
  "/analisis":     { plantilla: "tpl-analisis", titulo: "Análisis", controlador: montarAnalisis },
  "/metas":        { plantilla: "tpl-metas", titulo: "Metas de ahorro", controlador: montarMetas },
  "/perfil":       { plantilla: "tpl-perfil", titulo: "Perfil", controlador: montarPerfil },
};

let limpiezaPrevista = null;

export function navegar(ruta) {
  if (location.hash !== `#${ruta}`) location.hash = `#${ruta}`;
  else renderizar(); // misma ruta: forzar re-render (p. ej. tras login)
}

function rutaActual() {
  return (location.hash || "#/panel").slice(1) || "/panel";
}

/** Configura la capa principal (sidebar + topbar) una sola vez. */
function montarShell() {
  const app = document.getElementById("app");
  app.replaceChildren(plantilla("tpl-shell"));
  pintarIconos(app);

  const sidebar = document.getElementById("sidebar");
  const overlay = document.getElementById("nav-overlay");
  const btnMenu = document.getElementById("btn-menu");

  function alternarNav(abrir) {
    const abierto = abrir ?? !document.body.classList.contains("nav-abierta");
    document.body.classList.toggle("nav-abierta", abierto);
    overlay.hidden = !abierto;
    btnMenu.setAttribute("aria-expanded", String(abierto));
    btnMenu.setAttribute("aria-label", abierto ? "Cerrar menú de navegación" : "Abrir menú de navegación");
  }

  btnMenu.addEventListener("click", () => alternarNav());
  overlay.addEventListener("click", () => alternarNav(false));
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && document.body.classList.contains("nav-abierta")) alternarNav(false);
  });
  // Al navegar desde el menú móvil, cerrar el panel lateral
  sidebar.querySelector(".sidebar-nav").addEventListener("click", (e) => {
    if (e.target.closest("a")) alternarNav(false);
  });

  // Chip (enlace nativo) y avatar llevan al perfil
  document.getElementById("btn-avatar").addEventListener("click", () => navegar("/perfil"));

  // Cerrar sesión
  document.getElementById("btn-salir").addEventListener("click", async () => {
    try {
      const tokens = obtenerTokens();
      if (tokens?.refresh) await api.logout(tokens.refresh);
    } catch { /* la sesión local se cierra igualmente */ }
    limpiarTokens();
    toast("Sesión cerrada correctamente. ¡Hasta pronto!", "info");
    navegar("/login");
  });

  // Si la sesión expira (evento de api.js), volver al login
  window.addEventListener("flux:sesion-expirada", () => {
    toast("Tu sesión expiró. Inicia sesión de nuevo.", "error");
    navegar("/login");
  });

  // CTA global: nuevo movimiento (drawer del módulo transactions).
  // Import dinámico con await: requireDrawer() devolvía una Promise y
  // destructurar de ella dejaba abrirDrawerMovimiento como undefined.
  document.getElementById("btn-nuevo-movimiento").addEventListener("click", async () => {
    try {
      const { abrirDrawerMovimiento } = await import("../modules/transactions/drawer.js");
      abrirDrawerMovimiento(null, () => renderizar());
    } catch (error) {
      console.error("No se pudo abrir el drawer de movimiento:", error);
      toast("No se pudo abrir el formulario de movimiento", "error");
    }
  });

  // Campana de notificaciones (anomalías reales)
  configurarCampana();

  actualizarDatosUsuario();
}

/** Campana: consulta anomalías reales y muestra un panel desplegable. */
function configurarCampana() {
  const btn = document.getElementById("btn-campana");
  const menu = document.getElementById("campana-menu");
  const punto = document.getElementById("punto-notificacion");
  let cargado = false;

  async function cargarAnomalias() {
    try {
      const data = await api.panel.anomalias();
      menu.replaceChildren(
        el("h2", { class: "campana-titulo" }, "Notificaciones"),
        data.disponible && data.items?.length
          ? el("ul", { class: "notificacion-lista" },
            ...data.items.map((a) => el("li", {},
              el("button", {
                type: "button",
                class: "notificacion-item",
                onclick: () => { cerrar(); navegar("/analisis"); },
              },
                el("i", {
                  class: `notificacion-icono ${a.puntuacion >= 3 ? "critico" : "aviso"}`,
                  "aria-hidden": "true",
                }, "!"),
                el("div", { class: "notificacion-texto" },
                  el("p", { class: "notificacion-titulo" }, a.categoria,
                    el("data", { value: String(a.puntuacion.toFixed(2)) }, String(a.puntuacion.toFixed(2)))),
                  el("p", { class: "notificacion-detalle" },
                    "Movimiento atípico en ", a.descripcion || a.categoria, " (", a.metodo_pago, ")"))))))
          : el("p", { class: "nota" }, "Sin anomalías por ahora. ¡Buen control!"),
        el("div", { class: "campana-pie" },
          el("a", { class: "enlace-accion", href: "#/analisis" }, "Ver análisis completo"),
        ),
      );
      punto.hidden = !(data.disponible && data.items?.length);
      cargado = true;
    } catch {
      menu.replaceChildren(el("p", { class: "nota" }, "No se pudieron cargar las notificaciones."));
    }
  }

  function cerrar() {
    menu.hidden = true;
    btn.setAttribute("aria-expanded", "false");
  }

  btn.addEventListener("click", () => {
    const abrir = menu.hidden;
    if (abrir) {
      menu.hidden = false;
      btn.setAttribute("aria-expanded", "true");
      if (!cargado) {
        menu.replaceChildren(el("p", { class: "nota" }, "Cargando…"));
        cargarAnomalias();
      }
    } else cerrar();
  });
  document.addEventListener("click", (e) => {
    if (!e.target.closest(".campana")) cerrar();
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") cerrar();
  });
}

/** Rellena el chip de usuario del sidebar (datos cacheados). */
function actualizarDatosUsuario() {
  const usuario = obtenerUsuario();
  if (!usuario) return;
  document.getElementById("usuario-nombre").textContent = usuario.nombre_completo || usuario.username;
  document.getElementById("usuario-alias").textContent = `@${usuario.username}`;
  const texto = iniciales(usuario.nombre_completo || usuario.username);
  document.getElementById("avatar-iniciales").textContent = texto;
  document.getElementById("avatar-topbar").textContent = texto;
}

function actualizarNavegacionActiva(ruta) {
  document.querySelectorAll(".sidebar-nav a").forEach((enlace) => {
    if (enlace.dataset.ruta === ruta) enlace.setAttribute("aria-current", "page");
    else enlace.removeAttribute("aria-current");
  });
}

/** Renderiza la vista según el hash actual. */
async function renderizar() {
  let ruta = rutaActual();
  let vista = VISTAS[ruta] || VISTAS["/panel"];

  // Guardias de autenticación
  if (!vista.publica && !estaAutenticado()) {
    if (ruta !== "/login") return navegar("/login");
    vista = VISTAS["/login"];
  } else if (vista.publica && estaAutenticado()) {
    return navegar("/panel");
  }

  // Vista pública (login/registro): sin shell
  if (vista.publica) {
    if (limpiezaPrevista) { limpiezaPrevista(); limpiezaPrevista = null; }
    const app = document.getElementById("app");
    app.replaceChildren(plantilla(vista.plantilla));
    pintarIconos(app);
    await montarAuth(app.firstElementChild, ruta === "/registro");
    return;
  }

  // Vista protegida: montar shell si no existe aún
  if (!document.getElementById("contenido-main")) montarShell();

  actualizarNavegacionActiva(ruta);
  document.getElementById("titulo-seccion").textContent = vista.titulo;
  document.getElementById("selector-mes").hidden = !vista.mes;
  actualizarDatosUsuario();

  // Limpieza de la vista anterior (gráficos, listeners)
  if (limpiezaPrevista) { limpiezaPrevista(); limpiezaPrevista = null; }

  const main = document.getElementById("contenido-main");
  main.replaceChildren(plantilla(vista.plantilla));
  pintarIconos(main);
  main.focus({ preventScroll: true });
  window.scrollTo({ top: 0 });

  if (vista.controlador) limpiezaPrevista = await vista.controlador(main);
}

/** Arranque del router. */
export async function iniciarRouter() {
  // Refrescar el perfil cacheado si hay sesión (silencioso)
  if (estaAutenticado()) {
    try {
      const usuario = await api.miPerfil();
      guardarUsuario(usuario);
    } catch { /* si falla, las vistas mostrarán su propio error */ }
  }

  if (!location.hash) {
    location.replace(estaAutenticado() ? "#/panel" : "#/login");
  }
  window.addEventListener("hashchange", renderizar);
  // El cambio de moneda re-renderiza la vista para reflejar el formato
  window.addEventListener("flux:usuario-actualizado", () => {
    if (obtenerUsuario()) actualizarDatosUsuario();
  });
  await renderizar();
}
