"""Servicio del módulo auth: login, rotación de tokens y logout.

Flujo de tokens:
1. ``POST /auth/login``  -> access_token (30 min) + refresh_token (7 días).
2. El refresh token se guarda HASHEADO (SHA-256) en la BD: se puede revocar.
3. ``POST /auth/refresh`` -> rota el refresh token (el anterior queda
   revocado) y emite un access token nuevo.
4. ``POST /auth/logout``  -> revoca el refresh token indicado.
"""

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import utcnow
from app.core.security import (
    crear_access_token,
    crear_refresh_token,
    decodificar_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.modules.auth import repository
from app.modules.auth.google import derivar_username_base
from app.modules.auth.schemas import RefreshRequest, TokenOut
from app.modules.users import repository as usuarios_repo
from app.modules.users import service as usuarios_service
from app.modules.users.models import User
from app.modules.users.schemas import UserCreate

# Hash de una contraseña inexistente: se usa para gastar el mismo tiempo de
# cómputo cuando el usuario NO existe (mitigación de ataques de timing).
_HASH_SENYUELO = hash_password("contraseña-senyuelo-no-usar")

# Excepciones reutilizables: mensajes genéricos (no filtran la causa).
_ERROR_CREDENCIALES = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Usuario o contraseña incorrectos",
    headers={"WWW-Authenticate": "Bearer"},
)
_ERROR_SESION = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Sesión expirada o token inválido. Inicia sesión de nuevo.",
    headers={"WWW-Authenticate": "Bearer"},
)


async def _emitir_tokens(db: AsyncSession, usuario: User) -> TokenOut:
    """Crea el par de tokens y registra el refresh (hash) en la BD."""
    access = crear_access_token(usuario.id)
    refresh, expiracion = crear_refresh_token(usuario.id)
    await repository.guardar_refresh(db, usuario.id, hash_token(refresh), expiracion)

    preferencia = await usuarios_repo.obtener_preferencia(db, usuario.id)
    return TokenOut(
        access_token=access,
        refresh_token=refresh,
        usuario=usuarios_service.a_out(usuario, preferencia.moneda),
    )


async def registrar(db: AsyncSession, datos: UserCreate) -> User:
    """Crea la cuenta nueva (delega las reglas en el módulo users)."""
    return await usuarios_service.registrar(db, datos)


async def autenticar(db: AsyncSession, identificador: str, password: str) -> TokenOut:
    """Autentica con usuario o correo + contraseña y emite tokens.

    La comparación bcrypt se ejecuta SIEMPRE (aunque el usuario no exista)
    para igualar el tiempo de respuesta entre ambos casos.
    """
    usuario = await usuarios_repo.buscar_por_identificador(db, identificador)

    # Las cuentas solo-Google no tienen hash: se usa el señuelo para igualar
    # tiempos y responder el mismo 401 genérico (nunca 500).
    hash_a_verificar = (
        usuario.hashed_password if (usuario and usuario.hashed_password) else _HASH_SENYUELO
    )
    password_ok = verify_password(password, hash_a_verificar)

    if usuario is None or not password_ok or not usuario.is_active:
        raise _ERROR_CREDENCIALES

    return await _emitir_tokens(db, usuario)


async def renovar(db: AsyncSession, datos: RefreshRequest) -> TokenOut:
    """Intercambia un refresh token válido por un par nuevo (rotación).

    La fila del token se lee con bloqueo pesimista (``FOR UPDATE``) dentro
    de la transacción que gestiona ``get_db``: dos peticiones paralelas con
    el mismo refresh se serializan y solo una prospera (la otra ve el token
    ya revocado y recibe 401).
    """
    usuario_id = decodificar_token(datos.refresh_token, tipo_esperado="refresh")
    registro = None
    if usuario_id is not None:
        registro = await repository.buscar_por_hash_para_actualizar(
            db, hash_token(datos.refresh_token)
        )

    es_valido = (
        usuario_id is not None
        and registro is not None
        and registro.usuario_id == usuario_id
        and registro.revocado is None  # no revocado (logout)
        and registro.expira > utcnow()  # no expirado
    )
    if not es_valido:
        raise _ERROR_SESION

    usuario = await db.get(User, usuario_id)
    if usuario is None or not usuario.is_active:
        raise _ERROR_SESION

    # Rotación: el token presentado queda revocado y se emite uno nuevo.
    await repository.revocar(db, registro)
    return await _emitir_tokens(db, usuario)


async def cerrar_sesion(db: AsyncSession, usuario: User, datos: RefreshRequest) -> None:
    """Revoca el refresh token indicado (idempotente).

    Nunca revoca un token de otro usuario: el filtro por usuario_id sale
    del JWT (prevención de IDOR).
    """
    registro = await repository.buscar_por_hash(db, hash_token(datos.refresh_token))
    if registro is not None and registro.usuario_id == usuario.id:
        await repository.revocar(db, registro)


async def cerrar_sesion_en_todos(db: AsyncSession, usuario: User) -> None:
    """Revoca TODOS los refresh tokens activos del usuario autenticado."""
    await repository.revocar_todos(db, usuario.id)


async def autenticar_con_google(db: AsyncSession, claims: dict) -> TokenOut:
    """Autentica con un ID token de Google ya verificado y emite tokens.

    ``claims`` viene de ``google.verificar_id_token`` (firma, audiencia y
    expiración ya comprobadas). Aquí solo se aplica la política de cuenta:
    1. Si el ``sub`` ya está vinculado => entra directo.
    2. Si el correo verificado existe (cuenta con contraseña) => se vincula
       el ``sub`` (la contraseña queda intacta) y entra.
    3. Si no existe => se crea la cuenta (sin contraseña) y entra.
    El email debe estar verificado por Google; si no, 401 genérico.
    """
    google_sub = str(claims.get("sub") or "")
    email = str(claims.get("email") or "").strip().lower()
    if not google_sub or not email or claims.get("email_verified") is not True:
        raise _ERROR_SESION

    usuario = await usuarios_repo.buscar_por_google_sub(db, google_sub)
    if usuario is None:
        usuario = await usuarios_repo.buscar_por_email(db, email)
        if usuario is not None:
            # Vinculación automática: Google ya probó la propiedad del correo.
            usuario.google_sub = google_sub
            await db.flush()
        else:
            usuario = await _crear_cuenta_google(
                db,
                email=email,
                google_sub=google_sub,
                nombre=str(claims.get("name") or "").strip() or email.split("@")[0],
            )

    if not usuario.is_active:
        raise _ERROR_SESION
    return await _emitir_tokens(db, usuario)


async def _crear_cuenta_google(
    db: AsyncSession, *, email: str, google_sub: str, nombre: str
) -> User:
    """Crea la cuenta de un usuario nuevo de Google (sin contraseña).

    Resistente a condiciones de carrera: si dos peticiones paralelas
    intentan registrar la misma cuenta de Google, se captura IntegrityError
    en un savepoint para recuperar la cuenta ya creada o reintentar el username.
    """
    base = derivar_username_base(email)
    username = base
    sufijo = 0

    for _ in range(10):
        while await usuarios_repo.existe_usuario_o_email(db, username, email):
            existente = await usuarios_repo.buscar_por_email(db, email)
            if existente is not None:
                if existente.google_sub != google_sub:
                    existente.google_sub = google_sub
                    await db.flush()
                return existente
            sufijo += 1
            username = f"{base}_{sufijo}"

        try:
            async with db.begin_nested():
                return await usuarios_repo.crear(
                    db,
                    username=username,
                    email=email,
                    nombre_completo=nombre[:100] or username,
                    hashed_password=None,
                    google_sub=google_sub,
                )
        except IntegrityError:
            existente = await usuarios_repo.buscar_por_email(db, email)
            if existente is not None:
                if existente.google_sub != google_sub:
                    existente.google_sub = google_sub
                    await db.flush()
                return existente
            sufijo += 1
            username = f"{base}_{sufijo}"

    existente = await usuarios_repo.buscar_por_email(db, email)
    if existente is not None:
        return existente
    raise _ERROR_SESION
