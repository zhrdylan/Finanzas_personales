"""Configuración central de la aplicación.

Toda la configuración sensible (claves, credenciales de BD) se lee desde
variables de entorno o del archivo ``.env`` (nunca hardcodeada).
Ver ``.env.example`` para la documentación de cada variable.

Base de datos: únicamente MySQL 9.6 (driver aiomysql). No existe soporte
ni fallback a SQLite u otro motor; la URL debe empezar por ``mysql+aiomysql``.
"""

import logging
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger("app.config")

PREFIJO_URL_MYSQL = "mysql+aiomysql://"


class Settings(BaseSettings):
    """Parámetros de configuración de la aplicación."""

    # ------------------------------------------------------------------ #
    # Aplicación
    # ------------------------------------------------------------------ #
    APP_NAME: str = "Finanzas Personales"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"

    # ------------------------------------------------------------------ #
    # Seguridad / JWT
    # ------------------------------------------------------------------ #
    SECRET_KEY: str = ""  # OBLIGATORIA; fallo de arranque si falta
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30  # vida corta del token de acceso
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7  # vida del token de renovación

    # ------------------------------------------------------------------ #
    # Base de datos: MySQL 9.6 exclusivamente
    # ------------------------------------------------------------------ #
    DATABASE_URL: str = "mysql+aiomysql://root:@127.0.0.1:3306/finanzas_personales"

    # ------------------------------------------------------------------ #
    # CORS: solo el origen propio (comas para separar varios)
    # ------------------------------------------------------------------ #
    CORS_ORIGINS: str = "http://localhost:8000,http://127.0.0.1:8000"

    # ------------------------------------------------------------------ #
    # Rate limiting del login (freno a fuerza bruta)
    # ------------------------------------------------------------------ #
    LOGIN_RATE_LIMIT: str = "5/minute"

    # ------------------------------------------------------------------ #
    # Tasas de cambio (Frankfurter v2, consumo exclusivo del backend)
    # ------------------------------------------------------------------ #
    EXCHANGE_BASE_URL: str = "https://api.frankfurter.dev/v2"
    EXCHANGE_TIMEOUT_S: float = 8.0

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    @property
    def cors_origins_list(self) -> list[str]:
        """Convierte la cadena de orígenes separados por coma en lista."""
        return [origen.strip() for origen in self.CORS_ORIGINS.split(",") if origen.strip()]

    @property
    def host_base_datos(self) -> str:
        """Parte 'host:puerto/bd' de la URL (para mensajes de error sin credenciales)."""
        return self.DATABASE_URL.split("@")[-1]


@lru_cache
def get_settings() -> Settings:
    """Devuelve la configuración como singleton (caché) con validaciones."""
    settings = Settings()

    # La URL debe apuntar a MySQL: no se acepta ningún otro motor.
    if not settings.DATABASE_URL.startswith(PREFIJO_URL_MYSQL):
        raise RuntimeError(
            "DATABASE_URL debe usar MySQL 9.6 con el driver aiomysql "
            f"(empezar por '{PREFIJO_URL_MYSQL}'). Otros motores (SQLite, "
            "PostgreSQL, ...) no están soportados en este proyecto."
        )

    # Validaciones de seguridad en el arranque (fail-fast + avisos)
    if not settings.SECRET_KEY:
        raise RuntimeError(
            "SECRET_KEY no está definida. Copia .env.example a .env y genera "
            'una clave con: python -c "import secrets; print(secrets.token_hex(32))"'
        )
    if len(settings.SECRET_KEY) < 32:
        logger.warning(
            "SECRET_KEY es corta (%d caracteres); se recomiendan 64 hex (32 bytes).",
            len(settings.SECRET_KEY),
        )
    if "cambia-esta-clave" in settings.SECRET_KEY:
        logger.warning(
            "Estás usando la SECRET_KEY de ejemplo del .env.example. "
            "Genera una clave propia antes de desplegar."
        )
    return settings


settings = get_settings()
