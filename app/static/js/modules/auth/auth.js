/**
 * Vista de autenticación: iniciar sesión / crear cuenta (pestañas).
 * Diseño del prototipo: tarjeta centrada, logo con gradiente y conmutador.
 *
 * NOTA: NO existe acceso de demostración ni autenticación automática;
 * el único camino es registrarse o iniciar sesión con credenciales reales.
 */

import { api } from "../../services/endpoints.js";
import { guardarTokens, guardarUsuario } from "../../core/sesion.js";
import { navegar } from "../../core/router.js";
import { pintarIconos } from "../../utils/dom.js";
import { alertaFormulario, limpiarErrorEnEntrada, validarFormulario } from "../../utils/formularios.js";
import { toast } from "../../utils/ui.js";
import { instalarOjitos } from "../../utils/clave.js";

/** Marca la pestaña activa y alterna los formularios (y su bloque de Google). */
function alternarPestana(raiz, esRegistro) {
  raiz.querySelector("#tab-login").setAttribute("aria-selected", String(!esRegistro));
  raiz.querySelector("#tab-registro").setAttribute("aria-selected", String(esRegistro));
  raiz.querySelector("#form-login").hidden = esRegistro;
  raiz.querySelector("#form-registro").hidden = !esRegistro;
  // Cada bloque de Google acompaña a su formulario (solo uno visible a la vez).
  // Antes de que GIS termine de cargar, ambos quedan ocultos.
  const googleListo = raiz.dataset.googleListo === "1";
  raiz.querySelector("#google-bloque-login").hidden = esRegistro || !googleListo;
  raiz.querySelector("#google-bloque-registro").hidden = !esRegistro || !googleListo;
}

/** Carga el script de Google Identity Services una sola vez. */
let scriptGoogleEnCurso = null;

function cargarScriptGoogle() {
  if (window.google?.accounts?.id) return Promise.resolve();
  if (!scriptGoogleEnCurso) {
    scriptGoogleEnCurso = new Promise((resolver, rechazar) => {
      const script = document.createElement("script");
      script.src = "https://accounts.google.com/gsi/client";
      script.async = true;
      script.defer = true;
      script.onload = () => resolver();
      script.onerror = () => rechazar(new Error("No se pudo cargar Google"));
      document.head.append(script);
    }).catch((error) => { scriptGoogleEnCurso = null; throw error; });
  }
  return scriptGoogleEnCurso;
}

/** Muestra el error de Google en el bloque visible (login o registro). */
function mostrarErrorGoogle(raiz, mensaje) {
  for (const id of ["google-alerta-login", "google-alerta-registro"]) {
    const alerta = raiz.querySelector(`#${id}`);
    if (!alerta) continue;
    alerta.textContent = mensaje;
    alerta.hidden = !mensaje;
  }
}

/**
 * Inicializa el botón "Continuar con Google" si el backend lo habilitó.
 * Sin Client ID configurado (o sin internet) el bloque queda oculto y el
 * login con contraseña sigue intacto.
 */
async function inicializarGoogle(raiz) {
  let config = null;
  try {
    config = await api.googleConfig();
  } catch {
    return; // backend inaccesible: sin botón de Google
  }
  if (!config?.habilitado || !config?.client_id) return;
  try {
    await cargarScriptGoogle();
  } catch {
    return; // sin internet: sin botón de Google
  }
  if (!window.google?.accounts?.id) return;

  window.google.accounts.id.initialize({
    client_id: config.client_id,
    callback: async (respuesta) => {
      mostrarErrorGoogle(raiz, "");
      if (!respuesta?.credential) {
        mostrarErrorGoogle(raiz, "Google no devolvió credencial. Intenta de nuevo.");
        return;
      }
      try {
        const data = await api.loginGoogle(respuesta.credential);
        guardarTokens({ access: data.access_token, refresh: data.refresh_token });
        guardarUsuario(data.usuario);
        toast(`¡Bienvenido, ${data.usuario.nombre_completo}!`, "exito");
        navegar("/panel");
      } catch (error) {
        mostrarErrorGoogle(raiz, error.message);
      }
    },
    auto_select: false,
  });

  // Renderiza el botón con el ancho del BLOQUE (no del div vacío: con
  // align-items:center un div vacío mide 0 aunque esté visible y el botón
  // jamás se renderizaría). Fallback topado si el layout aún no resolvió.
  const botonesGoogle = ["google-btn-login", "google-btn-registro"];
  const renderizados = new Set();
  function anchoBoton(contenedor) {
    const bloque = contenedor.parentElement;
    const medido = bloque ? bloque.clientWidth : 0;
    if (medido > 0) return Math.min(medido, 400);
    return 0;
  }
  function renderizarBoton(boton) {
    if (renderizados.has(boton)) return true;
    const contenedor = raiz.querySelector(`#${boton}`);
    if (!contenedor) return false;
    let ancho = anchoBoton(contenedor);
    if (ancho === 0) {
      // Layout sin resolver o pestaña oculta: se reintenta en el próximo
      // frame; si sigue oculta queda pendiente al observador de pestañas.
      requestAnimationFrame(() => {
        if (renderizados.has(boton)) return;
        const reintento = raiz.querySelector(`#${boton}`);
        if (!reintento || anchoBoton(reintento) === 0) return;
        renderizarBoton(boton);
      });
      return false;
    }
    try {
      window.google.accounts.id.renderButton(contenedor, {
        theme: "outline", size: "large", shape: "pill", width: ancho,
      });
    } catch (error) {
      console.info("No se pudo renderizar el botón de Google:", error);
      return false;
    }
    renderizados.add(boton);
    return true;
  }

  // Marca GIS como listo y muestra solo el bloque de la pestaña activa ANTES
  // de medir (medir un bloque oculto daría 0 y GIS usaría su ancho por defecto).
  raiz.dataset.googleListo = "1";
  const esRegistro = raiz.querySelector("#tab-registro").getAttribute("aria-selected") === "true";
  alternarPestana(raiz, esRegistro);

  for (const boton of botonesGoogle) renderizarBoton(boton);
  // El bloque de la otra pestaña se renderiza perezoso al mostrarse.
  const observador = new MutationObserver(() => {
    let pendientes = 0;
    for (const boton of botonesGoogle) {
      if (!renderizados.has(boton) && !renderizarBoton(boton)) pendientes += 1;
    }
    if (pendientes === 0) observador.disconnect();
  });
  observador.observe(raiz, { attributes: true, attributeFilter: ["hidden"], subtree: true });
  pintarIconos(raiz);
}

export function montarAuth(raiz, esRegistro = false) {
  // El logo ya es un <img> en la plantilla (logo-icon.png transparente);
  // no inyectar SVG aquí para no romperlo.

  const tabLogin = raiz.querySelector("#tab-login");
  const tabRegistro = raiz.querySelector("#tab-registro");
  tabLogin.addEventListener("click", () => alternarPestana(raiz, false));
  tabRegistro.addEventListener("click", () => alternarPestana(raiz, true));
  alternarPestana(raiz, esRegistro);
  instalarOjitos(raiz);

  /* ------------------------------ Login ------------------------------ */
  const formLogin = raiz.querySelector("#form-login");
  limpiarErrorEnEntrada(formLogin);
  formLogin.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (!validarFormulario(formLogin)) return;
    alertaFormulario(formLogin, "");

    const boton = formLogin.querySelector("button[type=submit]");
    boton.disabled = true;
    try {
      const data = await api.login(
        formLogin.querySelector("#login-usuario").value.trim(),
        formLogin.querySelector("#login-password").value,
      );
      guardarTokens({ access: data.access_token, refresh: data.refresh_token });
      guardarUsuario(data.usuario);
      toast(`¡Bienvenido de nuevo, ${data.usuario.nombre_completo}!`, "exito");
      navegar("/panel");
    } catch (error) {
      alertaFormulario(formLogin, error.message);
    } finally {
      boton.disabled = false;
    }
  });

  /* ----------------------------- Registro ---------------------------- */
  const formRegistro = raiz.querySelector("#form-registro");
  limpiarErrorEnEntrada(formRegistro);
  formRegistro.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (!validarFormulario(formRegistro)) return;
    alertaFormulario(formRegistro, "");

    const password = formRegistro.querySelector("#reg-password").value;
    const password2 = formRegistro.querySelector("#reg-password2").value;
    if (password !== password2) {
      const err = raiz.querySelector("#err-reg-password2");
      err.textContent = "Las contraseñas no coinciden.";
      err.hidden = false;
      return;
    }

    const boton = formRegistro.querySelector("button[type=submit]");
    boton.disabled = true;
    try {
      await api.registro({
        nombre_completo: formRegistro.querySelector("#reg-nombre").value.trim(),
        username: formRegistro.querySelector("#reg-usuario").value.trim(),
        email: formRegistro.querySelector("#reg-email").value.trim(),
        password,
      });
      toast("Cuenta creada. Inicia sesión con tus credenciales.", "exito");
      navegar("/login");
    } catch (error) {
      alertaFormulario(formRegistro, error.message);
    } finally {
      boton.disabled = false;
    }
  });

  /* ------------------------- Google (si habilitado) ------------------------ */
  inicializarGoogle(raiz);
}
