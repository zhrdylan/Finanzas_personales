"""Excepciones del módulo exports."""

from app.shared.exceptions import ErrorDominio


class ExportacionFallida(ErrorDominio):
    """No se pudo generar el archivo de exportación."""

    status_code = 500
    mensaje = "No se pudo generar la exportación. Intenta más tarde."
