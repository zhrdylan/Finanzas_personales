"""Punto de entrada de la aplicación: API FastAPI + servidor del frontend SPA.

Arranque (desde la raíz del proyecto):
    python -m uvicorn app.main:app --reload
Documentación interactiva: http://127.0.0.1:8000/docs

Arquitectura: Monolito Modular. Los routers se importan desde los módulos
de negocio (app/modules/*) y las excepciones de dominio se traducen aquí
a respuestas HTTP coherentes.
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy import text

from app import __version__
from app.core.config import settings
from app.core.database import engine
from app.core.rate_limit import limiter
from app.modules.auth.router import router as auth_router
from app.modules.categories.router import router as categories_router
from app.modules.dashboard.router import router as dashboard_router
from app.modules.exchange_rates.exceptions import TasaNoDisponible
from app.modules.exchange_rates.router import router as tasas_router
from app.modules.exports.router import router as exports_router
from app.modules.goals.router import router as goals_router
from app.modules.transactions.router import router as transactions_router
from app.modules.users.router import router as users_router
from app.shared.exceptions import Conflicto, EntradaInvalida, NoEncontrado

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-7s %(name)s - %(message)s",
)
logger = logging.getLogger("app.main")

BASE_DIR = Path(__file__).resolve().parent  # carpeta app/
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Ciclo de vida: verifica la conexión a MySQL al arrancar (fail-fast)."""
    try:
        async with engine.connect() as conexion:
            await conexion.execute(text("SELECT 1"))
        logger.info("Conexión a MySQL verificada (%s).", settings.host_base_datos)
    except Exception as exc:  # noqa: BLE001
        logger.error("No se pudo conectar a la base de datos: %s", exc)
        raise RuntimeError(
            f"Verifica DATABASE_URL en tu .env (host: {settings.host_base_datos}). "
            "Con Laragon: inicia MySQL desde el panel antes de arrancar el backend."
        ) from exc
    logger.info(
        "%s v%s iniciada. Docs: http://127.0.0.1:8000/docs",
        settings.APP_NAME,
        settings.APP_VERSION,
    )
    yield
    await engine.dispose()
    logger.info("Conexiones a la base de datos cerradas.")


app = FastAPI(
    title=settings.APP_NAME,
    version=__version__,
    description=(
        "API de gestión de finanzas personales: usuarios, categorías, "
        "movimientos, metas de ahorro, moneda configurable, panel analítico "
        "con predicción y detección de anomalías."
    ),
    lifespan=lifespan,
)

# ------------------------------ Middlewares -------------------------------- #
app.add_middleware(
    CORSMiddleware,
    # CORS restringido: solo los orígenes propios definidos en .env
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)
app.add_middleware(GZipMiddleware, minimum_size=1024)  # respuestas comprimidas

# ------------------------------ Rate limiting ------------------------------- #
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ------------------------------ Routers (módulos) ---------------------------- #
app.include_router(auth_router, prefix=settings.API_V1_PREFIX)
app.include_router(users_router, prefix=settings.API_V1_PREFIX)
app.include_router(categories_router, prefix=settings.API_V1_PREFIX)
app.include_router(transactions_router, prefix=settings.API_V1_PREFIX)
app.include_router(goals_router, prefix=settings.API_V1_PREFIX)
app.include_router(dashboard_router, prefix=settings.API_V1_PREFIX)
app.include_router(tasas_router, prefix=settings.API_V1_PREFIX)
app.include_router(exports_router, prefix=settings.API_V1_PREFIX)


# ------------------------------ Frontend (SPA) ------------------------------ #
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
async def indice():
    """Sirve el SPA (templates/index.html)."""
    return FileResponse(TEMPLATES_DIR / "index.html")


# ------------------------------ Salud ---------------------------------------- #
@app.get(f"{settings.API_V1_PREFIX}/health", tags=["salud"], summary="Healthcheck")
async def salud() -> dict[str, str]:
    """Endpoint de verificación básica."""
    return {"estado": "ok", "version": __version__}


# ------------------------------ Errores -------------------------------------- #
@app.exception_handler(RequestValidationError)
async def error_validacion(request: Request, exc: RequestValidationError):
    """Convierte los errores 422 en mensajes claros (sin datos internos)."""
    detalles = []
    for error in exc.errors():
        campo = ".".join(str(p) for p in error.get("loc", []) if p not in ("body",))
        detalles.append(f"{campo or 'dato'}: {error.get('msg', 'inválido')}")
    return JSONResponse(
        status_code=422,
        content={"detail": "Datos inválidos", "errores": detalles[:10]},
    )


@app.exception_handler(NoEncontrado)
async def error_no_encontrado(request: Request, exc: NoEncontrado):
    """Excepción de dominio: recurso inexistente o ajeno (anti-IDOR)."""
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.mensaje})


@app.exception_handler(Conflicto)
async def error_conflicto(request: Request, exc: Conflicto):
    """Excepción de dominio: conflicto con el estado actual."""
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.mensaje})


@app.exception_handler(EntradaInvalida)
async def error_entrada_invalida(request: Request, exc: EntradaInvalida):
    """Excepción de dominio: regla de negocio violada (422)."""
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.mensaje})


@app.exception_handler(TasaNoDisponible)
async def error_tasa_no_disponible(request: Request, exc: TasaNoDisponible):
    """Sin tasa del proveedor ni en caché (503 controlado, reintentable)."""
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.mensaje})


@app.exception_handler(Exception)
async def error_no_controlado(request: Request, exc: Exception):
    """Errores no controlados: se registran en el servidor, pero al cliente
    solo se le devuelve un mensaje genérico (sin filtrar detalles técnicos)."""
    logger.exception("Error no controlado en %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Error interno del servidor. Intenta más tarde."},
    )
