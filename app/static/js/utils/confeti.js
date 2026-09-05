/**
 * Confeti de celebración en canvas 2D (vanilla, sin dependencias ni CDN).
 *
 * Uso: celebrarConConfeti() al cumplirse una meta de ahorro.
 * - Canvas decorativo a pantalla completa: no intercepta clics, se
 *   auto-elimina al terminar (sin fugas aunque se celebre varias veces).
 * - Respeta `prefers-reduced-motion`: en ese caso no lanza nada visual
 *   (la vista ya muestra el toast "¡Meta alcanzada!").
 * - Colores de la marca Flux + dorado de celebración.
 */

const COLORES_CONFETI = ["#0053ce", "#51d9fe", "#55ddac", "#f5b301", "#ffffff"];
const PIEZAS = 130;
const DURACION_MS = 3000;

/** ¿El usuario prefiere movimiento reducido? (WCAG 2.2 AA). */
function movimientoReducido() {
  return window.matchMedia?.("(prefers-reduced-motion: reduce)").matches ?? false;
}

function piezaAleatoria(ancho) {
  return {
    x: Math.random() * ancho,
    y: -20 - Math.random() * 40,
    ancho: 6 + Math.random() * 6,
    alto: 8 + Math.random() * 8,
    velocidadY: 2 + Math.random() * 3,
    derivaX: -1.5 + Math.random() * 3,
    rotacion: Math.random() * Math.PI * 2,
    velocidadRotacion: -0.15 + Math.random() * 0.3,
    color: COLORES_CONFETI[Math.floor(Math.random() * COLORES_CONFETI.length)],
  };
}

/** Lanza la celebración. No hace nada con movimiento reducido. */
export function celebrarConConfeti() {
  if (movimientoReducido()) return;

  const canvas = document.createElement("canvas");
  canvas.className = "confeti-canvas";
  canvas.setAttribute("aria-hidden", "true");
  document.body.append(canvas);

  const contexto = canvas.getContext("2d");
  if (!contexto) {
    canvas.remove();
    return;
  }

  function ajustarTamano() {
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
  }
  ajustarTamano();
  window.addEventListener("resize", ajustarTamano);

  const piezas = Array.from({ length: PIEZAS }, () => piezaAleatoria(canvas.width));
  const inicio = performance.now();
  let animacion = 0;

  function dibujar(ahora) {
    const progreso = (ahora - inicio) / DURACION_MS;
    contexto.clearRect(0, 0, canvas.width, canvas.height);

    for (const pieza of piezas) {
      pieza.x += pieza.derivaX + Math.sin((ahora + pieza.y) / 200);
      pieza.y += pieza.velocidadY;
      pieza.rotacion += pieza.velocidadRotacion;
      // Desvanece en el último 25% para un cierre suave.
      contexto.globalAlpha = progreso > 0.75 ? Math.max(0, 1 - (progreso - 0.75) / 0.25) : 1;
      contexto.save();
      contexto.translate(pieza.x, pieza.y);
      contexto.rotate(pieza.rotacion);
      contexto.fillStyle = pieza.color;
      contexto.fillRect(-pieza.ancho / 2, -pieza.alto / 2, pieza.ancho, pieza.alto);
      contexto.restore();
    }
    contexto.globalAlpha = 1;

    if (progreso < 1) {
      animacion = requestAnimationFrame(dibujar);
    } else {
      terminar();
    }
  }

  function terminar() {
    cancelAnimationFrame(animacion);
    window.removeEventListener("resize", ajustarTamano);
    canvas.remove();
  }

  animacion = requestAnimationFrame(dibujar);
  // Red de seguridad: garantiza la limpieza aunque el rAF se interrumpa.
  window.setTimeout(terminar, DURACION_MS + 500);
}
