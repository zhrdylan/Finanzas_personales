"""Rate limiting compartido (slowapi, almacenamiento en memoria).

Se aplica sobre todo al login: 5 intentos por minuto e IP por defecto
(configurable con LOGIN_RATE_LIMIT). Para despliegues multi-worker se
recomienda migrar el almacenamiento a Redis.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

# Límite por defecto vacío: cada ruta sensible aplica su propio límite
# (ver app/modules/auth/router.py -> POST /auth/login).
limiter = Limiter(key_func=get_remote_address)
