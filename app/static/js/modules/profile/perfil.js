/**
 * Vista Perfil: tarjeta de usuario, datos de la cuenta, preferencias
 * (moneda de visualización COP/USD/EUR persistida en MySQL), cambio de
 * contraseña, cierre de sesiones y exportación de datos (CSV/PDF
 * generados en el backend).
 *
 * NOTA: la exportación JSON/respaldo sigue eliminada por decisión de
 * arquitectura; solo existen CSV y PDF ("Exportar mis datos").
 */

import { api } from "../../services/endpoints.js";
import { guardarUsuario, limpiarTokens, monedaActual, obtenerUsuario, notificarUsuarioActualizado } from "../../core/sesion.js";
import { navegar } from "../../core/router.js";
import { el, ICONOS } from "../../utils/dom.js";
import { dinero, ejemploDeFormato, iniciales } from "../../utils/formato.js";
import { alertaFormulario, limpiarErrorEnEntrada, validarFormulario } from "../../utils/formularios.js";
import { confirmarAccion } from "../../utils/modal.js";
import { toast } from "../../utils/ui.js";
import { instalarOjitos } from "../../utils/clave.js";

const MESES_REGISTRO = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"];

export async function montarPerfil(main) {
  const usuario = obtenerUsuario();
  if (!usuario) return null;
  instalarOjitos(main);

  /* --------------------------- Tarjeta de perfil -------------------------- */
  main.querySelector("#perfil-avatar").textContent =
    iniciales(usuario.nombre_completo || usuario.username);
  main.querySelector("#perfil-nombre").textContent = usuario.nombre_completo;
  main.querySelector("#perfil-correo").textContent = usuario.email;

  const fecha = new Date(usuario.fecha_registro);
  const mesISO = Number.isNaN(fecha.getTime())
    ? ""
    : `${fecha.getFullYear()}-${String(fecha.getMonth() + 1).padStart(2, "0")}`;
  main.querySelector("#perfil-miembro").replaceChildren(
    "Miembro desde ",
    el("time", { datetime: mesISO },
      `${MESES_REGISTRO[fecha.getMonth()]} ${fecha.getFullYear()}`),
  );

  /* ----------------------------- Datos de cuenta -------------------------- */
  const formPerfil = main.querySelector("#form-perfil");
  const inputNombre = main.querySelector("#perf-nombre-input");
  inputNombre.value = usuario.nombre_completo;
  limpiarErrorEnEntrada(formPerfil);

  formPerfil.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (!validarFormulario(formPerfil)) return;
    try {
      const actualizado = await api.actualizarPerfil({
        nombre_completo: inputNombre.value.trim(),
      });
      guardarUsuario(actualizado);
      notificarUsuarioActualizado();
      main.querySelector("#perfil-nombre").textContent = actualizado.nombre_completo;
      toast("Perfil actualizado", "exito");
    } catch (error) {
      toast(error.message, "error");
    }
  });

  /* ------------------------- Preferencias: moneda ------------------------- */
  const selectMoneda = main.querySelector("#preferencia-moneda");
  selectMoneda.value = usuario.moneda || "COP";

  // Ejemplos de formato (COP / USD / EUR) junto a la preferencia
  main.querySelector("#ejemplo-cop").textContent = `COP: ${ejemploDeFormato("COP")}`;
  main.querySelector("#ejemplo-usd").textContent = `USD: ${ejemploDeFormato("USD")}`;
  main.querySelector("#ejemplo-eur").textContent = `EUR: ${ejemploDeFormato("EUR")}`;

  selectMoneda.addEventListener("change", async () => {
    const anterior = monedaActual();
    try {
      const preferencias = await api.actualizarPreferencias({ moneda: selectMoneda.value });
      const actualizado = { ...obtenerUsuario(), moneda: preferencias.moneda };
      guardarUsuario(actualizado);
      notificarUsuarioActualizado();
      toast(`Moneda actualizada a ${preferencias.moneda}. Ejemplo: ${dinero(1250000, preferencias.moneda)}`, "exito");
      // Si la moneda anterior era distinta, re-renderizar para re-formatear todo
      if (anterior !== preferencias.moneda) {
        navegar("/perfil");
      }
    } catch (error) {
      selectMoneda.value = obtenerUsuario()?.moneda || "COP";
      toast(error.message, "error");
    }
  });

  /* --------------------------- Cambio de contraseña ----------------------- */
  const formPassword = main.querySelector("#form-password");
  limpiarErrorEnEntrada(formPassword);

  formPassword.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (!validarFormulario(formPassword)) return;
    alertaFormulario(formPassword, "");

    const actual = main.querySelector("#pass-actual").value;
    const nueva = main.querySelector("#pass-nueva").value;
    const confirmar = main.querySelector("#pass-confirmar").value;

    if (nueva !== confirmar) {
      alertaFormulario(formPassword, "Las contraseñas nuevas no coinciden");
      return;
    }

    try {
      await api.cambiarPassword({ password_actual: actual, password_nueva: nueva });
      toast("Contraseña actualizada. Inicia sesión de nuevo.", "exito");
      limpiarTokens();
      navegar("/login");
    } catch (error) {
      alertaFormulario(formPassword, error.message);
    }
  });

  /* --------------------------- Exportar mis datos ------------------------- */
  const btnCsv = main.querySelector("#btn-exportar-csv");
  const btnPdf = main.querySelector("#btn-exportar-pdf");
  const estadoExport = main.querySelector("#exportar-estado");

  function mostrarEstadoExport(mensaje) {
    if (!estadoExport) return;
    estadoExport.textContent = mensaje || "";
    estadoExport.hidden = !mensaje;
  }

  if (btnCsv && btnPdf) {
    // Evita descargas simultáneas: deshabilita ambos mientras se genera.
    async function exportar(boton, formato, descargar) {
      if (boton.disabled) return;
      btnCsv.disabled = true;
      btnPdf.disabled = true;
      mostrarEstadoExport(`Generando ${formato}…`);
      try {
        const nombre = await descargar();
        mostrarEstadoExport("");
        toast(`${formato} descargado (${nombre})`, "exito");
      } catch (error) {
        mostrarEstadoExport(`No se pudo generar el ${formato}: ${error.message}`);
        toast(error.message, "error");
      } finally {
        btnCsv.disabled = false;
        btnPdf.disabled = false;
      }
    }
    btnCsv.addEventListener("click", () => exportar(btnCsv, "CSV", () => api.exports.csv()));
    btnPdf.addEventListener("click", () => exportar(btnPdf, "PDF", () => api.exports.pdf()));
  }

  /* ------------------------------ Cerrar sesiones ------------------------- */
  main.querySelector("#btn-logout-todos").addEventListener("click", async () => {
    const ok = await confirmarAccion({
      titulo: "Cerrar todas las sesiones",
      mensaje: "Se cerrará tu sesión en todos los dispositivos (incluida esta). ¿Continuar?",
      textoConfirmar: "Cerrar sesiones",
    });
    if (!ok) return;
    try {
      await api.logoutTodos();
    } finally {
      limpiarTokens();
      toast("Sesiones cerradas en todos los dispositivos", "info");
      navegar("/login");
    }
  });

  return null;
}
