/**
 * Endpoints de la API agrupados por recurso.
 * Cada módulo de vista consume este archivo; ningún módulo construye URLs
 * propias (evita lógica de API repetida).
 */

import peticion, { descargarArchivo } from "../core/api.js";

export const api = {
  /* Autenticación */
  registro: (datos) => peticion("/auth/registro", { metodo: "POST", cuerpo: datos, autenticado: false }),
  login: (usuario, password) => peticion("/auth/login", {
    metodo: "POST", autenticado: false,
    cuerpo: new URLSearchParams({ username: usuario, password }),
  }),
  logout: (refreshToken) => peticion("/auth/logout", {
    metodo: "POST", cuerpo: { refresh_token: refreshToken },
  }),
  logoutTodos: () => peticion("/auth/logout-todos", { metodo: "POST" }),

  /* Usuarios */
  miPerfil: () => peticion("/usuarios/me"),
  actualizarPerfil: (datos) => peticion("/usuarios/me", { metodo: "PATCH", cuerpo: datos }),
  cambiarPassword: (datos) => peticion("/usuarios/me/password", { metodo: "PATCH", cuerpo: datos }),
  misPreferencias: () => peticion("/usuarios/me/preferencias"),
  actualizarPreferencias: (datos) => peticion("/usuarios/me/preferencias", { metodo: "PATCH", cuerpo: datos }),

  /* Categorías */
  categorias: {
    listar: () => peticion("/categorias"),
    crear: (datos) => peticion("/categorias", { metodo: "POST", cuerpo: datos }),
    actualizar: (id, datos) => peticion(`/categorias/${id}`, { metodo: "PATCH", cuerpo: datos }),
    eliminar: (id) => peticion(`/categorias/${id}`, { metodo: "DELETE" }),
  },

  /* Movimientos */
  movimientos: {
    listar: (params) => peticion("/movimientos", { params }),
    crear: (datos) => peticion("/movimientos", { metodo: "POST", cuerpo: datos }),
    actualizar: (id, datos) => peticion(`/movimientos/${id}`, { metodo: "PATCH", cuerpo: datos }),
    eliminar: (id) => peticion(`/movimientos/${id}`, { metodo: "DELETE" }),
  },

  /* Metas de ahorro */
  metas: {
    listar: () => peticion("/metas"),
    crear: (datos) => peticion("/metas", { metodo: "POST", cuerpo: datos }),
    actualizar: (id, datos) => peticion(`/metas/${id}`, { metodo: "PATCH", cuerpo: datos }),
    eliminar: (id) => peticion(`/metas/${id}`, { metodo: "DELETE" }),
    aportar: (id, monto) => peticion(`/metas/${id}/aportes`, { metodo: "POST", cuerpo: { monto } }),
  },

  /* Panel y análisis (moneda opcional: por defecto la preferencia) */
  panel: {
    completo: (mes, moneda) => peticion("/panel/completo", { params: { mes, moneda } }),
    resumen: (mes, moneda) => peticion("/panel/resumen", { params: { mes, moneda } }),
    gastosPorCategoria: (mes, moneda) => peticion("/panel/gastos-por-categoria", { params: { mes, moneda } }),
    evolucion: (moneda) => peticion("/panel/evolucion-mensual", { params: { moneda } }),
    prediccion: (moneda) => peticion("/panel/prediccion", { params: { moneda } }),
    anomalias: () => peticion("/panel/anomalias"),
  },

  /* Tasas de cambio (transparencia: las resuelve el backend) */
  tasas: {
    obtener: (base, quote, fecha) => peticion("/tasas", { params: { base, quote, fecha } }),
  },

  /* Exportación de datos (CSV/PDF generados en el backend) */
  exports: {
    csv: (params) => descargarArchivo("/exports/transactions.csv", { params }),
    pdf: (params) => descargarArchivo("/exports/transactions.pdf", { params }),
  },
};
