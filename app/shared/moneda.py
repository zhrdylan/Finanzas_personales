"""Monedas soportadas por el proyecto (Fase 2: multi-moneda real).

Cada movimiento/meta guarda su moneda original. La preferencia del usuario
define la moneda de visualización: el backend convierte con el módulo
``exchange_rates`` (tasas reales de Frankfurter v2 + caché en MySQL) sin
modificar los valores originales. El formato (símbolo, separadores,
decimales) se aplica en el frontend según el locale.
"""

from typing import Literal

# Monedas soportadas: Peso colombiano, Dólar estadounidense y Euro.
Moneda = Literal["COP", "USD", "EUR"]

MONEDAS_VALIDAS: tuple[str, ...] = ("COP", "USD", "EUR")
MONEDA_POR_DEFECTO: str = "COP"
