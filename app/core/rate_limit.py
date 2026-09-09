"""Rate limiting compartido (slowapi, almacenamiento en memoria).

Se aplica sobre todo al login: 5 intentos por minuto e IP por defecto
(configurable con LOGIN_RATE_LIMIT). Para despliegues multi-worker se
recomienda migrar el almacenamiento a Redis.
"""

from fastapi import Request
from slowapi import Limiter


def obtener_ip_cliente(request: Request) -> str:
    """Extrae la IP real del cliente considerando proxies inversos (Railway, Nginx, etc.).

    Prioridad:
    1. Cabecera X-Forwarded-For (la primera IP corresponde al cliente original).
    2. Cabecera X-Real-IP.
    3. Dirección de socket directa (request.client.host).
    4. Fallback a 127.0.0.1 si no hay información de conexión.
    """
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()

    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip()

    if request.client and request.client.host:
        return request.client.host

    return "127.0.0.1"


# Límite por defecto vacío: cada ruta sensible aplica su propio límite
# (ver app/modules/auth/router.py -> POST /auth/login).
limiter = Limiter(key_func=obtener_ip_cliente)
