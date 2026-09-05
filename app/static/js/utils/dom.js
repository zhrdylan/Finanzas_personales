/**
 * Utilidades de interfaz: creación de nodos y plantillas.
 *
 * PRINCIPIO DE SEGURIDAD (anti-XSS): TODO el DOM dinámico se construye con
 * createElement + textContent mediante el helper `el()`. Nunca se usa
 * innerHTML con datos del usuario o de la API.
 */

/**
 * Crea un elemento con atributos e hijos.
 * Los hijos string se insertan como texto seguro (textContent).
 *
 * ej.: el("button", { class: "btn", type: "button", onclick: fn }, "Guardar")
 */
export function el(etiqueta, atributos = {}, ...hijos) {
  const nodo = document.createElement(etiqueta);
  for (const [clave, valor] of Object.entries(atributos)) {
    if (valor === null || valor === undefined || valor === false) continue;
    if (clave === "class") nodo.className = valor;
    else if (clave === "dataset") Object.assign(nodo.dataset, valor);
    else if (clave === "style") Object.assign(nodo.style, valor);
    else if (clave.startsWith("on") && typeof valor === "function") {
      nodo.addEventListener(clave.slice(2), valor);
    } else if (valor === true) nodo.setAttribute(clave, "");
    else nodo.setAttribute(clave, String(valor));
  }
  for (const hijo of hijos.flat(Infinity)) {
    if (hijo === null || hijo === undefined || hijo === false) continue;
    nodo.append(hijo instanceof Node ? hijo : document.createTextNode(String(hijo)));
  }
  return nodo;
}

/** Clona el primer elemento de un <template> del index.html. */
export function plantilla(id) {
  const nodo = document.getElementById(id);
  if (!nodo) throw new Error(`Plantilla no encontrada: ${id}`);
  return nodo.content.firstElementChild.cloneNode(true);
}

/**
 * Inserta el SVG inline de un icono del set local (equivalente libre a
 * lucide, sin CDN). Funciona con cualquier placeholder con [data-icono]
 * (i, svg, etc.) y lo reemplaza directamente por el <svg>, sin wrapper.
 */
export function pintarIconos(raiz = document) {
  raiz.querySelectorAll("[data-icono]").forEach((nodo) => {
    const nombre = nodo.dataset.icono;
    const ruta = ICONOS[nombre];
    if (!ruta) return;
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.setAttribute("viewBox", "0 0 24 24");
    svg.setAttribute("fill", "none");
    svg.setAttribute("stroke", "currentColor");
    svg.setAttribute("stroke-width", "2");
    svg.setAttribute("stroke-linecap", "round");
    svg.setAttribute("stroke-linejoin", "round");
    svg.setAttribute("aria-hidden", "true");
    // Preservar clases del placeholder para no romper el layout
    // (p. ej. nav-icono, campo-icono, kpi-icono).
    if (nodo.getAttribute("class")) svg.setAttribute("class", nodo.getAttribute("class"));
    svg.innerHTML = ruta; // estático, definido en este archivo (no hay datos de usuario)
    nodo.replaceWith(svg);
  });
}

/** Set de iconos inline (rutas SVG estáticas). */
export const ICONOS = {
  panel: '<rect x="3" y="3" width="7" height="9" rx="1"/><rect x="14" y="3" width="7" height="5" rx="1"/><rect x="14" y="12" width="7" height="9" rx="1"/><rect x="3" y="16" width="7" height="5" rx="1"/>',
  movimientos: '<line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/><line x1="3" y1="6" x2="3.01" y2="6"/><line x1="3" y1="12" x2="3.01" y2="12"/><line x1="3" y1="18" x2="3.01" y2="18"/>',
  categorias: '<path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z"/><line x1="7" y1="7" x2="7.01" y2="7"/>',
  analisis: '<line x1="3" y1="17" x2="9" y2="11"/><line x1="9" y1="17" x2="15" y2="11"/><line x1="15" y1="17" x2="21" y2="11"/><polyline points="3 7 9 7 15 3 21 3"/>',
  metas: '<path d="M19 5c-1.5 0-2.8 1.4-3 2-3.5-1.5-11-.3-11 5 0 1.8 0 3 2 4.5V20h4v-3h4v3h4v-4c1-.5 1.7-1 2-2h2v-4h-2c0-1-.5-1.5-1-2h0V5z"/><path d="M2 9v1c0 1.1.9 2 2 2h1"/><circle cx="16" cy="11" r="1"/>',
  salir: '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/>',
  menu: '<line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/>',
  campana: '<path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/>',
  mas: '<line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>',
  flechaArriba: '<line x1="12" y1="19" x2="12" y2="5"/><polyline points="5 12 12 5 19 12"/>',
  flechaAbajo: '<line x1="12" y1="5" x2="12" y2="19"/><polyline points="19 12 12 19 5 12"/>',
  flechaDerecha: '<line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/>',
  billetera: '<path d="M21 12V7H5a2 2 0 0 1 0-4h14v4"/><path d="M3 5v14a2 2 0 0 0 2 2h16v-5"/><path d="M18 12a2 2 0 0 0 0 4h4v-4Z"/>',
  tendencia: '<polyline points="22 7 13.5 15.5 8.5 10.5 2 17"/><polyline points="16 7 22 7 22 13"/>',
  advertencia: '<path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>',
  buscar: '<circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>',
  calendario: '<rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/>',
  limpiar: '<line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>',
  descargar: '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>',
  filtroLimpiar: '<polygon points="22 3 2 3 10 12.5 10 19 14 21 14 12.5 22 3"/><line x1="18" y1="15" x2="22" y2="19"/><line x1="22" y1="15" x2="18" y2="19"/>',
  editar: '<path d="M17 3a2.85 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z"/>',
  papelera: '<polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>',
  vertical: '<circle cx="12" cy="12" r="1"/><circle cx="12" cy="5" r="1"/><circle cx="12" cy="19" r="1"/>',
  getion: '<circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>',
  cerebro: '<path d="M12 2a4 4 0 0 0-4 4c-2 0-4 1.8-4 4a4 4 0 0 0 2 3.5V16a4 4 0 0 0 4 4h4a4 4 0 0 0 4-4v-2.5A4 4 0 0 0 20 10c0-2.2-2-4-4-4a4 4 0 0 0-4-4Z"/><line x1="12" y1="6" x2="12" y2="18"/>',
  corona: '<path d="M6 9H4.5a2.5 2.5 0 0 1 0-5H6"/><path d="M18 9h1.5a2.5 2.5 0 0 0 0-5H18"/><path d="M4 22h16"/><path d="M10 14.66V17c0 .55-.47.98-.97 1.21C7.85 18.75 7 20.24 7 22"/><path d="M14 14.66V17c0 .55.47.98.97 1.21C16.15 18.75 17 20.24 17 22"/><path d="M18 2H6v7a6 6 0 0 0 12 0V2Z"/>',
  monedas: '<circle cx="8" cy="8" r="6"/><path d="M18.09 10.37A6 6 0 1 1 10.34 18"/><path d="M7 6h1v4"/><path d="m16.71 13.88.7.71-2.82 2.82"/>',
  chulo: '<polyline points="20 6 9 17 4 12"/>',
  chulitoCirculo: '<circle cx="12" cy="12" r="10"/><polyline points="8 12 11 15 16 9"/>',
  cambio: '<path d="M3 3v5h5"/><path d="M21 21v-5h-5"/><path d="M21 8a9 9 0 0 0-15-4.5L3 8"/><path d="M3 16a9 9 0 0 0 15 4.5l3-4.5"/>',
  ajustes: '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1Z"/>',
  ojo: '<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/>',
  ojoTachado: '<path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94"/><path d="M9.53 9.53a3 3 0 1 0 4.24 4.24"/><path d="M14.12 14.12L9.88 9.88"/><path d="M9.88 9.88L14.12 14.12"/><line x1="1" y1="1" x2="23" y2="23"/>',
};
