/**
 * Punto de entrada del frontend (SPA).
 * Carga el enrutador, que decide la vista según el hash y la sesión.
 */

import { iniciarRouter } from "./core/router.js";
import { guardarUsuario, obtenerUsuario } from "./core/sesion.js";

// Refresca el chip de usuario del sidebar cuando el perfil cambia
window.addEventListener("flux:usuario-actualizado", () => {
  const usuario = obtenerUsuario();
  if (!usuario) return;
  const nombre = document.getElementById("usuario-nombre");
  const alias = document.getElementById("usuario-alias");
  const avatar = document.getElementById("avatar-iniciales");
  const avatarTop = document.getElementById("avatar-topbar");
  const texto = (usuario.nombre_completo || usuario.username)
    .split(/\s+/).slice(0, 2).map((p) => p[0].toUpperCase()).join("") || "?";
  if (nombre) nombre.textContent = usuario.nombre_completo || usuario.username;
  if (alias) alias.textContent = `@${usuario.username}`;
  if (avatar) avatar.textContent = texto;
  if (avatarTop) avatarTop.textContent = texto;
});

// El backend (respuestas de login/refresh) puede actualizar el usuario cacheado
window.addEventListener("flux:usuario-cacheado", (e) => {
  if (e.detail) guardarUsuario(e.detail);
});

document.addEventListener("DOMContentLoaded", () => {
  iniciarRouter().catch((error) => {
    console.error("Error al iniciar la aplicación:", error);
    const app = document.getElementById("app");
    app.replaceChildren();
    app.append(
      (() => {
        const div = document.createElement("div");
        div.className = "pantalla-carga";
        const p = document.createElement("p");
        p.textContent = "No se pudo iniciar la aplicación. Recarga la página.";
        div.append(p);
        return div;
      })(),
    );
  });
});
