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

/** Marca la pestaña activa y alterna los formularios. */
function alternarPestana(raiz, esRegistro) {
  raiz.querySelector("#tab-login").setAttribute("aria-selected", String(!esRegistro));
  raiz.querySelector("#tab-registro").setAttribute("aria-selected", String(esRegistro));
  raiz.querySelector("#form-login").hidden = esRegistro;
  raiz.querySelector("#form-registro").hidden = !esRegistro;
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
}
