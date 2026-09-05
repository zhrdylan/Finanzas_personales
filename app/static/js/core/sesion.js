/**
 * Gestión de la sesión en el navegador (tokens + usuario cacheado).
 *
 * El access token vive 30 min y el refresh 7 días; api.js se encarga de
 * renovarlos. El usuario cacheado incluye la moneda de visualización.
 */

import { CLAVE_TOKENS, CLAVE_USUARIO } from "./config.js";

export function obtenerTokens() {
  try {
    return JSON.parse(localStorage.getItem(CLAVE_TOKENS) || "null");
  } catch {
    return null;
  }
}

export function guardarTokens(tokens) {
  localStorage.setItem(CLAVE_TOKENS, JSON.stringify(tokens));
}

export function limpiarTokens() {
  localStorage.removeItem(CLAVE_TOKENS);
  localStorage.removeItem(CLAVE_USUARIO);
}

export function estaAutenticado() {
  return Boolean(obtenerTokens()?.access);
}

export function guardarUsuario(usuario) {
  localStorage.setItem(CLAVE_USUARIO, JSON.stringify(usuario));
}

export function obtenerUsuario() {
  try {
    return JSON.parse(localStorage.getItem(CLAVE_USUARIO) || "null");
  } catch {
    return null;
  }
}

/** Moneda de visualización vigente (por defecto COP). */
export function monedaActual() {
  return obtenerUsuario()?.moneda || "COP";
}

/** Aviso a la app de que cambió el usuario (perfil/moneda). */
export function notificarUsuarioActualizado() {
  window.dispatchEvent(new CustomEvent("flux:usuario-actualizado"));
}
