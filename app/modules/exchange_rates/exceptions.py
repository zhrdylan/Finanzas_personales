"""Excepciones del módulo exchange_rates.

``TasaNoDisponible`` (503) se usa cuando el proveedor externo falla y no
existe ninguna tasa almacenada válida: la app sigue funcionando con datos
locales, pero la conversión solicitada no puede resolverse.
"""

from app.shared.exceptions import ErrorDominio


class TasaNoDisponible(ErrorDominio):
    """Sin tasa del proveedor ni en caché para el par/fecha pedidos."""

    status_code = 503
    mensaje = "Tasa de cambio no disponible en este momento. Intenta más tarde."


class ProveedorTasasCaido(ErrorDominio):
    """El proveedor externo no respondió (timeout, red o 5xx). Interna."""

    status_code = 503
    mensaje = "El proveedor de tasas no responde"


class TasaSinDatos(ErrorDominio):
    """El proveedor respondió que no tiene datos (404 o payload inválido)."""

    status_code = 404
    mensaje = "Sin datos de tasa para la fecha solicitada"
