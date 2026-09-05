/**
 * Configuración global del frontend.
 */

export const API_BASE = "/api/v1";

/** Claves de almacenamiento local de la sesión. */
export const CLAVE_TOKENS = "flux.tokens";
export const CLAVE_USUARIO = "flux.usuario";

/** Ruta tras iniciar sesión y a la que se vuelve al cerrarla. */
export const RUTA_INICIO = "/panel";

/** Formato de las monedas soportadas (locale + decimales).
 *  La moneda es de SOLO VISUALIZACIÓN: no se convierten montos. */
export const MONEDAS = {
  COP: { locale: "es-CO", decimales: 0, ejemplo: "$ 1.250.000" },
  USD: { locale: "en-US", decimales: 2, ejemplo: "$1,250.00" },
  EUR: { locale: "es-ES", decimales: 2, ejemplo: "1.250,00 €" },
};

/** Colores por defecto para la paleta de categorías (prototipo). */
export const PALETA_COLORES = [
  "#FF6B6B", "#4ECDC4", "#FFE66D", "#1A535C",
  "#9D4EDD", "#F3722C", "#0053ce", "#55ddac",
];

/** Meses cortos en español (independientes del locale del navegador). */
export const MESES_CORTOS = [
  "ene", "feb", "mar", "abr", "may", "jun",
  "jul", "ago", "sep", "oct", "nov", "dic",
];
