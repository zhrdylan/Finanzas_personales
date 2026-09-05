/**
 * Utilidad ojito mostrar/ocultar contraseña (Opción A - auto-enhance).
 *
 * - Detecta todos los input[type="password"] dentro de un contenedor
 * - Los envuelve en .campo-password y añade botón .btn-ojo a la derecha
 * - Alterna type password<->text, aria-label y icono ojo/ojoTachado
 * - Idempotente: no duplica si ya existe (dataset.ojoInstalado)
 * - Accesible: button type="button", no submit, mantiene foco en input
 */

import { el, pintarIconos } from "./dom.js";

function crearBotonOjo(input) {
  const btn = el("button", {
    type: "button",
    class: "btn-ojo",
    "aria-label": "Mostrar contraseña",
    "aria-pressed": "false",
    title: "Mostrar contraseña",
    tabindex: "0",
  }, el("i", { "data-icono": "ojo", "aria-hidden": "true" }));

  btn.addEventListener("click", () => {
    const visible = input.type === "text";
    input.type = visible ? "password" : "text";
    const mostrar = visible;
    btn.setAttribute("aria-label", mostrar ? "Mostrar contraseña" : "Ocultar contraseña");
    btn.setAttribute("title", mostrar ? "Mostrar contraseña" : "Ocultar contraseña");
    btn.setAttribute("aria-pressed", String(!visible));
    // Cambiar icono
    const icono = btn.querySelector("i, svg");
    if (icono) {
      const reemplazo = el("i", {
        "data-icono": mostrar ? "ojo" : "ojoTachado",
        "aria-hidden": "true",
      });
      icono.replaceWith(reemplazo);
      pintarIconos(btn);
    }
    // Mantener foco en el input para seguir escribiendo
    input.focus({ preventScroll: true });
    // Mover cursor al final
    try {
      const len = input.value.length;
      input.setSelectionRange(len, len);
    } catch { /* inputs sin selection */ }
  });

  return btn;
}

export function instalarOjitos(raiz = document) {
  const inputs = raiz.querySelectorAll('input[type="password"]');
  for (const input of inputs) {
    if (input.dataset.ojoInstalado === "1") continue;
    // Solo inputs dentro de .campo (los de formularios)
    const campo = input.closest(".campo");
    if (!campo) continue;
    // Envolver visualmente: crear div campo-password alrededor del input
    // Si ya existe wrapper, usarlo
    let wrapper = campo.querySelector(".campo-password");
    // Si el campo ya tiene la estructura, solo añadir botón si falta
    if (input.parentElement.classList.contains("campo-password")) {
      wrapper = input.parentElement;
    } else {
      wrapper = document.createElement("div");
      wrapper.className = "campo-password";
      // Mantener el estilo flex del campo original
      input.parentNode.insertBefore(wrapper, input);
      wrapper.appendChild(input);
    }
    if (wrapper.querySelector(".btn-ojo")) {
      input.dataset.ojoInstalado = "1";
      continue;
    }
    const btn = crearBotonOjo(input);
    wrapper.appendChild(btn);
    pintarIconos(btn);
    input.dataset.ojoInstalado = "1";
  }
}

/**
 * Observa cambios dinámicos (por si se inyectan nuevos forms por plantilla)
 * Opcional: usar MutationObserver para auto-instalar en SPA al cambiar vista
 */
export function observarOjitos(raiz = document.body) {
  const observer = new MutationObserver((mutaciones) => {
    for (const m of mutaciones) {
      for (const nodo of m.addedNodes) {
        if (nodo instanceof HTMLElement) {
          if (nodo.matches && nodo.matches('input[type="password"]')) {
            instalarOjitos(nodo.parentElement || raiz);
          } else if (nodo.querySelectorAll) {
            const hayPasswords = nodo.querySelectorAll('input[type="password"]').length;
            if (hayPasswords) instalarOjitos(nodo);
          }
        }
      }
    }
  });
  observer.observe(raiz, { childList: true, subtree: true });
  return () => observer.disconnect();
}
