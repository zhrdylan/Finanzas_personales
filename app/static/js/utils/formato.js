/**
 * Formateo de moneda y fechas según la moneda configurada por el usuario.
 *
 * La moneda es de SOLO VISUALIZACIÓN (no hay conversión de tasas):
 * un movimiento de 100000 se muestra como 100000 en la moneda activa.
 * Formatos por moneda:
 *   COP → $ 1.250.000   (es-CO, sin decimales)
 *   USD → $1,250.00     (en-US)
 *   EUR → 1.250,00 €    (es-ES)
 */

import { MESES_CORTOS, MONEDAS } from "../core/config.js";
import { monedaActual } from "../core/sesion.js";

const cacheFormatos = new Map();

function formatoDe(moneda) {
  if (!cacheFormatos.has(moneda)) {
    const config = MONEDAS[moneda] || MONEDAS.COP;
    cacheFormatos.set(
      moneda,
      new Intl.NumberFormat(config.locale, {
        style: "currency",
        currency: moneda,
        minimumFractionDigits: config.decimales,
        maximumFractionDigits: config.decimales,
      }),
    );
  }
  return cacheFormatos.get(moneda);
}

/** Formatea un importe con la moneda de visualización del usuario. */
export function dinero(valor, moneda = monedaActual()) {
  const numero = Number(valor || 0);
  const formateado = formatoDe(moneda).format(Math.abs(numero));
  if (numero < 0) return `-${formateado}`;
  return formateado;
}

/** Igual que dinero(), pero con signo explícito (+/-). */
export function dineroConSigno(valor, moneda = monedaActual()) {
  const numero = Number(valor || 0);
  if (numero > 0) return `+${dinero(numero, moneda)}`;
  return dinero(numero, moneda);
}

/** "2026-08-15" -> "15 ago 2026" (formato del prototipo). */
export function fechaCorta(iso) {
  if (!iso) return "";
  const [anio, mes, dia] = iso.split("-");
  return `${dia} ${MESES_CORTOS[Number(mes) - 1] || ""}, ${anio}`;
}

/** "2026-08" -> "ago 2026". */
export function etiquetaMes(mesIso) {
  const [anio, mes] = mesIso.split("-");
  return `${MESES_CORTOS[Number(mes) - 1]} ${anio}`;
}

/** Mes actual en "YYYY-MM" según el reloj LOCAL del navegador. */
export function mesActual() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
}

/** Fecha de hoy en "YYYY-MM-DD". */
export function hoyISO() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

/** "Ana García" -> "AG" (iniciales para el avatar). */
export function iniciales(nombreCompleto) {
  return (nombreCompleto || "?")
    .split(/\s+/).filter(Boolean).slice(0, 2)
    .map((p) => p[0].toUpperCase()).join("") || "?";
}

/** Ejemplos de formato para la pantalla de preferencias. */
export function ejemploDeFormato(moneda) {
  return MONEDAS[moneda]?.ejemplo || "";
}
