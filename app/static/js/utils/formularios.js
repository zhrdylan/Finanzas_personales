/**
 * Validación de formularios accesible (API nativa + mensajes junto al campo).
 */

/** Muestra u oculta el mensaje de error de un campo. */
function marcarError(campo, mensaje) {
  const id = campo.id ? `err-${campo.id}` : null;
  const parrafo = id ? document.getElementById(id) : null;
  if (mensaje) {
    campo.setAttribute("aria-invalid", "true");
    if (parrafo) { parrafo.textContent = mensaje; parrafo.hidden = false; }
  } else {
    campo.removeAttribute("aria-invalid");
    if (parrafo) { parrafo.textContent = ""; parrafo.hidden = true; }
  }
}

function mensajeDeValidacion(campo) {
  const v = campo.validity;
  if (v.valueMissing) return "Este campo es obligatorio.";
  if (v.typeMismatch && campo.type === "email") return "Escribe un correo válido.";
  if (v.patternMismatch) return "Solo letras, números y guion bajo.";
  if (v.tooShort) return `Debe tener al menos ${campo.minLength} caracteres.`;
  if (v.rangeUnderflow) return `El valor mínimo es ${campo.min}.`;
  if (v.stepMismatch || v.badInput) return "Valor inválido.";
  return campo.validationMessage || "Valor inválido.";
}

/**
 * Valida un formulario con la API de validación nativa y muestra los
 * errores junto a cada campo. Devuelve true si todo es válido.
 */
export function validarFormulario(form) {
  let primeroInvalido = null;
  for (const campo of form.querySelectorAll("input, select, textarea")) {
    const valido = campo.checkValidity();
    marcarError(campo, valido ? "" : mensajeDeValidacion(campo));
    if (!valido && !primeroInvalido) primeroInvalido = campo;
  }
  if (primeroInvalido) primeroInvalido.focus();
  return !primeroInvalido;
}

/** Limpia el error de un campo al escribir (para listeners 'input'). */
export function limpiarErrorEnEntrada(form) {
  form.addEventListener("input", (e) => {
    if (e.target instanceof HTMLElement && e.target.closest(".campo")) {
      marcarError(e.target, "");
      e.target.setCustomValidity("");
    }
  });
}

/** Muestra un mensaje de error general del formulario. */
export function alertaFormulario(form, mensaje) {
  const parrafo = form.querySelector(".alerta");
  if (parrafo) {
    parrafo.textContent = mensaje || "";
    parrafo.hidden = !mensaje;
  }
}
