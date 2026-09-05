/**
 * Cliente HTTP de la API.
 *
 * - Adjunta el access token (Bearer) a cada petición autenticada.
 * - Si recibe 401, intenta RENOVAR los tokens una sola vez (con
 *   single-flight para evitar carreras entre peticiones paralelas) y
 *   repite la petición original.
 * - Si la renovación falla, cierra la sesión y notifica a la aplicación
 *   mediante el evento "flux:sesion-expirada".
 */

import { API_BASE } from "./config.js";
import {
  estaAutenticado,
  guardarTokens,
  guardarUsuario,
  limpiarTokens,
  obtenerTokens,
} from "./sesion.js";

/** Error de API con código HTTP. */
export class ErrorApi extends Error {
  constructor(status, mensaje) {
    super(mensaje);
    this.status = status;
    this.name = "ErrorApi";
  }
}

function _cerrarSesionExpirada() {
  limpiarTokens();
  window.dispatchEvent(new CustomEvent("flux:sesion-expirada"));
}

/* ------------------------------------------------------------------ *
 * Renovación con single-flight (una sola renovación a la vez)
 * ------------------------------------------------------------------ */

let renovacionEnCurso = null;

async function renovarTokens() {
  const tokens = obtenerTokens();
  if (!tokens?.refresh) throw new ErrorApi(401, "Sesión expirada");

  if (!renovacionEnCurso) {
    renovacionEnCurso = (async () => {
      const respuesta = await fetch(`${API_BASE}/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: tokens.refresh }),
      });
      if (!respuesta.ok) throw new ErrorApi(401, "Sesión expirada");
      const data = await respuesta.json();
      guardarTokens({ access: data.access_token, refresh: data.refresh_token });
      guardarUsuario(data.usuario);
      return data.access_token;
    })().finally(() => { renovacionEnCurso = null; });
  }
  return renovacionEnCurso;
}

/* ------------------------------------------------------------------ *
 * Petición base
 * ------------------------------------------------------------------ */

function mensajeDeError(data, status) {
  let detalle = data?.detail ?? data?.error;
  if (Array.isArray(detalle)) {
    detalle = detalle.map((d) => {
      const campo = Array.isArray(d.loc) ? d.loc[d.loc.length - 1] : "dato";
      return `${campo}: ${d.msg}`;
    }).join(" · ");
  }
  if (!detalle && Array.isArray(data?.errores)) detalle = data.errores.join(" · ");
  if (!detalle) detalle = `Error del servidor (${status})`;
  return typeof detalle === "string" ? detalle : "Error en la solicitud";
}

/**
 * Realiza una petición a la API.
 * @param {string} ruta     Ruta relativa (p. ej. "/movimientos").
 * @param {object} opciones { metodo, cuerpo, autenticado, reintento, params }
 */
async function peticion(ruta, {
  metodo = "GET", cuerpo, autenticado = true, reintento = true, params,
} = {}) {
  let url = `${API_BASE}${ruta}`;
  if (params) {
    const qs = new URLSearchParams();
    for (const [clave, valor] of Object.entries(params)) {
      if (valor !== "" && valor !== null && valor !== undefined) qs.append(clave, valor);
    }
    const texto = qs.toString();
    if (texto) url += `?${texto}`;
  }

  const cabeceras = {};
  let cuerpoFinal;
  if (cuerpo instanceof URLSearchParams) {
    cuerpoFinal = cuerpo; // fetch asigna el Content-Type del formulario
  } else if (cuerpo !== undefined) {
    cabeceras["Content-Type"] = "application/json";
    cuerpoFinal = JSON.stringify(cuerpo);
  }
  const tokens = obtenerTokens();
  if (autenticado && tokens?.access) {
    cabeceras["Authorization"] = `Bearer ${tokens.access}`;
  }

  const respuesta = await fetch(url, {
    method: metodo, headers: cabeceras, body: cuerpoFinal,
  });

  // 401 con sesión activa: intentar renovar UNA vez y repetir
  if (respuesta.status === 401 && autenticado && reintento && obtenerTokens()?.refresh) {
    try {
      await renovarTokens();
      return peticion(ruta, { metodo, cuerpo, autenticado, reintento: false, params });
    } catch {
      _cerrarSesionExpirada();
      throw new ErrorApi(401, "Tu sesión expiró. Inicia sesión de nuevo.");
    }
  }

  if (!respuesta.ok) {
    let data = null;
    try { data = await respuesta.json(); } catch { /* respuesta sin JSON */ }
    throw new ErrorApi(respuesta.status, mensajeDeError(data, respuesta.status));
  }

  if (respuesta.status === 204) return null;
  return respuesta.json();
}

/**
 * Descarga un archivo binario (CSV/PDF) disparando la descarga del navegador.
 * Reutiliza la autenticación y la renovación de sesión de peticion().
 * @param {string} ruta     Ruta relativa (p. ej. "/exports/transactions.csv").
 * @param {object} opciones { params, reintento }
 * @returns {Promise<string>} nombre del archivo descargado.
 */
export async function descargarArchivo(ruta, { params, reintento = true } = {}) {
  let url = `${API_BASE}${ruta}`;
  if (params) {
    const qs = new URLSearchParams();
    for (const [clave, valor] of Object.entries(params)) {
      if (valor !== "" && valor !== null && valor !== undefined) qs.append(clave, valor);
    }
    const texto = qs.toString();
    if (texto) url += `?${texto}`;
  }

  const tokens = obtenerTokens();
  const cabeceras = {};
  if (tokens?.access) cabeceras["Authorization"] = `Bearer ${tokens.access}`;

  const respuesta = await fetch(url, { headers: cabeceras });

  if (respuesta.status === 401 && reintento && obtenerTokens()?.refresh) {
    try {
      await renovarTokens();
      return descargarArchivo(ruta, { params, reintento: false });
    } catch {
      _cerrarSesionExpirada();
      throw new ErrorApi(401, "Tu sesión expiró. Inicia sesión de nuevo.");
    }
  }

  if (!respuesta.ok) {
    let data = null;
    try { data = await respuesta.json(); } catch { /* respuesta sin JSON */ }
    throw new ErrorApi(respuesta.status, mensajeDeError(data, respuesta.status));
  }

  const dispuesto = respuesta.headers.get("Content-Disposition") || "";
  const coincidencia = dispuesto.match(/filename="([^"]+)"/);
  const nombre = (coincidencia && coincidencia[1]) || "flux_exportacion";

  const blob = await respuesta.blob();
  const enlace = document.createElement("a");
  const objetoUrl = URL.createObjectURL(blob);
  enlace.href = objetoUrl;
  enlace.download = nombre;
  document.body.append(enlace);
  enlace.click();
  enlace.remove();
  setTimeout(() => URL.revokeObjectURL(objetoUrl), 4000);
  return nombre;
}

export { estaAutenticado };
export default peticion;
