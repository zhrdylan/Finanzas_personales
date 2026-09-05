"""Excepciones de dominio compartidas.

Los servicios lanzan estas excepciones; ``app.main`` las traduce a
respuestas HTTP coherentes. Así los routers quedan libres de lógica y los
servicios no dependen de FastAPI.
"""


class ErrorDominio(Exception):
    """Base de las excepciones de dominio."""

    status_code = 500
    mensaje = "Error interno"

    def __init__(self, mensaje: str | None = None) -> None:
        super().__init__(mensaje or self.mensaje)
        self.mensaje = mensaje or self.mensaje


class NoEncontrado(ErrorDominio):
    """El recurso no existe o pertenece a otro usuario (anti-IDOR: mismo 404)."""

    status_code = 404
    mensaje = "Recurso no encontrado"


class Conflicto(ErrorDominio):
    """Colisión con el estado actual (duplicados, recursos en uso, ...)."""

    status_code = 409
    mensaje = "Conflicto con el estado actual"


class EntradaInvalida(ErrorDominio):
    """Regla de negocio violada en los datos (equivale a 422)."""

    status_code = 422
    mensaje = "Datos inválidos"
