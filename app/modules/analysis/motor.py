"""Motor de análisis puro: predicción y anomalías con Pandas/Scikit-learn.

Las funciones de este módulo NO acceden a la base de datos: reciben las
filas ya leídas (fecha, monto, ...) y devuelven los resultados. Esto permite
probarlas con unit tests y mantiene la frontera del módulo ``analysis``:
SOLO LECTURA de datos financieros, nunca modificaciones.
"""

import calendar
from datetime import date
from decimal import Decimal

import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.linear_model import LinearRegression

from app.modules.analysis.schemas import AnomaliaOut, AnomaliasOut, PrediccionOut

# ----------------------------- Parámetros --------------------------------- #
# Detección robusta con Z-score modificado (mediana ± MAD): inmune a que un
# único outlier infle la dispersión (techo del Z clásico) y al ruido de la
# conversión de moneda entre valores casi idénticos.
UMBRAL_Z_MODIFICADO = 3.5  # z_mod >= 3.5 se considera anómalo (estándar)
# Desvío relativo mínimo cuando no hay dispersión observada (MAD == 0):
# ignora polvo de punto flotante; 1 % o más sí se reporta.
UMBRAL_DESVIO_RELATIVO = 0.01
# Bandas de severidad sobre el Z modificado (métrica universal, comparable
# entre métodos): moderada 3.5–10, alta 10–50, crítica > 50.
BANDA_SEVERIDAD_ALTA = 10.0
BANDA_SEVERIDAD_CRITICA = 50.0
MIN_MUESTRAS_ANALISIS = 10  # mínimo global para intentar el análisis
MIN_MUESTRAS_IF = 30  # mínimo por tipo para usar IsolationForest
CONTAMINACION_IF = 0.05  # proporción esperada de anomalías
MAX_ANOMALIAS = 10  # límite de resultados devueltos
TOLERANCIA_TENDENCIA = 0.05  # pendiente relativa ±5% => "estable"
# Tope finito de puntuación: el Z modificado puede ser infinito (MAD == 0)
# e `inf` no es JSON válido (rompería la API y el frontend).
TOPE_PUNTUACION = 9999.0


# ----------------------------- Utilidades --------------------------------- #
def restar_meses(base: date, n: int) -> date:
    """Fecha equivalente a 'base' menos n meses (día 1)."""
    total = base.year * 12 + (base.month - 1) - n
    return date(total // 12, total % 12 + 1, 1)


def rango_mes(anio: int, mes: int) -> tuple[date, date]:
    """Primer y último día del mes indicado."""
    inicio = date(anio, mes, 1)
    fin = date(anio, mes, calendar.monthrange(anio, mes)[1])
    return inicio, fin


def a_decimal(valor: float) -> Decimal:
    """Convierte un float de Pandas a Decimal legible (2 decimales)."""
    return Decimal(str(round(float(valor), 2)))


def z_modificado(valor: float, mediana: float, mad: float) -> float:
    """Z-score modificado (robusto): 0.6745 * |x - mediana| / MAD.

    A diferencia del Z clásico, el outlier no infla la dispersión que lo
    mide (la mediana de valores casi idénticos no se mueve con el ruido).
    Si ``mad`` es 0 (todos iguales), lo distinto de la mediana es outlier
    por definición (infinito) y lo igual puntúa 0.
    """
    if mad <= 0:
        return float("inf") if valor != mediana else 0.0
    return 0.6745 * abs(valor - mediana) / mad


def severidad_de(z_mod: float) -> str:
    """Banda de severidad sobre el Z modificado (escala universal)."""
    if z_mod > BANDA_SEVERIDAD_CRITICA:
        return "critica"
    if z_mod >= BANDA_SEVERIDAD_ALTA:
        return "alta"
    return "moderada"


def desvio_relativo(valor: float, mediana: float) -> float:
    """Desvío relativo a la mediana (|x - m| / |m|), para grupos sin dispersión.

    Con MAD == 0 el Z modificado sería infinito para cualquier desvío (no
    distinguiría €460 de €50000): aquí la magnitud sí importa y se expresa
    en tanto por uno (×100 = % de desvío, comparable con las bandas).
    """
    if mediana == 0:
        return float("inf") if valor != 0 else 0.0
    return abs(valor - mediana) / abs(mediana)


# ----------------------------- Predicción --------------------------------- #
def calcular_prediccion(filas: list[tuple[date, Decimal]]) -> PrediccionOut:
    """Predice el gasto del próximo mes con regresión lineal.

    ``filas`` son pares (fecha, monto) de TODOS los gastos históricos del
    usuario. Modelo: y = a·x + b, donde x es el índice del mes (0, 1, 2, ...)
    e y el total gastado ese mes. Modelo simple e interpretable, suficiente
    para detectar la tendencia general de los gastos.
    """
    if not filas:
        return PrediccionOut(
            disponible=False,
            mensaje="Aún no tienes gastos registrados para entrenar el modelo.",
        )

    df = pd.DataFrame(filas, columns=["fecha", "monto"])
    df["monto"] = df["monto"].astype(float)
    df["mes"] = pd.to_datetime(df["fecha"]).dt.strftime("%Y-%m")
    serie = df.groupby("mes")["monto"].sum().sort_index()

    # Rellenar meses intermedios sin gastos con 0 (serie continua)
    indice_completo = list(
        pd.period_range(serie.index[0], serie.index[-1], freq="M").strftime("%Y-%m")
    )
    serie = serie.reindex(indice_completo, fill_value=0.0)

    n = len(serie)
    if n < 2:
        return PrediccionOut(
            disponible=False,
            meses_analizados=n,
            mensaje="Se necesitan al menos 2 meses con gastos para ajustar la regresión lineal.",
        )

    x = [[i] for i in range(n)]  # meses como variable independiente
    y = serie.to_numpy()  # total gastado por mes

    modelo = LinearRegression().fit(x, y)
    valor = max(0.0, round(float(modelo.predict([[n]])[0]), 2))
    r2 = round(float(modelo.score(x, y)), 4)

    # Tendencia: pendiente relativa a la media mensual (con tolerancia del 5 %)
    media = float(y.mean())
    pendiente = float(modelo.coef_[0])
    if media > 0:
        relativa = pendiente / media
        tendencia = (
            "ascendente"
            if relativa > TOLERANCIA_TENDENCIA
            else "descendente"
            if relativa < -TOLERANCIA_TENDENCIA
            else "estable"
        )
    else:
        tendencia = "estable"

    mes_predicho = (pd.Period(serie.index[-1], freq="M") + 1).strftime("%Y-%m")

    return PrediccionOut(
        disponible=True,
        mes_predicho=mes_predicho,
        valor_predicho=valor,
        meses_analizados=n,
        tendencia=tendencia,
        r2=r2,
    )


# ----------------------------- Anomalías ----------------------------------- #
def calcular_anomalias(
    movimientos: list[dict],
) -> AnomaliasOut:
    """Detecta movimientos atípicos sobre datos ya leídos.

    ``movimientos`` es una lista de dicts con las claves:
    ``id, fecha, descripcion, tipo, monto (Decimal), categoria, metodo_pago``.

    Estrategia por tipo de movimiento (gastos e ingresos se analizan por
    separado porque sus escalas de monto son distintas):
    - Con 30 o más muestras: IsolationForest (contaminación 5 %).
    - Con 10 a 29 muestras:  Z-score modificado, mediana ± MAD (>= 3.5).
    - Sin dispersión observada (MAD == 0): desvío relativo a la mediana.
    La severidad (moderada/alta/crítica) se gradúa en escala comparable
    entre métodos.
    """
    total = len(movimientos)
    if total < MIN_MUESTRAS_ANALISIS:
        return AnomaliasOut(
            disponible=False,
            total_analizados=total,
            mensaje=(
                f"Se necesitan al menos {MIN_MUESTRAS_ANALISIS} movimientos "
                f"para el análisis (tienes {total})."
            ),
        )

    df = pd.DataFrame(
        {
            "tipo": [m["tipo"] for m in movimientos],
            "monto": [float(m["monto"]) for m in movimientos],
        }
    )

    encontrados: list[tuple[dict, float, str]] = []
    metodos: set[str] = set()

    for tipo in ("gasto", "ingreso"):
        sub = df[df["tipo"] == tipo]
        if len(sub) < MIN_MUESTRAS_ANALISIS:
            continue  # pocas muestras de este tipo: no se analiza

        # Referencia robusta del grupo (sirve para detectar y para graduar).
        mediana = float(sub["monto"].median())
        mad = float((sub["monto"] - mediana).abs().median())
        sin_dispersion = mad <= 0

        if len(sub) >= MIN_MUESTRAS_IF:
            # ---- IsolationForest (aprendizaje no supervisado) ----
            metodos.add("IsolationForest")
            modelo = IsolationForest(contamination=CONTAMINACION_IF, random_state=42)
            etiquetas = modelo.fit_predict(sub[["monto"]])
            # decision_function: mayor = más normal => se niega para que
            # mayor puntuación signifique "más anómalo".
            puntuaciones = -modelo.decision_function(sub[["monto"]])
            for i, pos in enumerate(sub.index):
                if etiquetas[i] == -1:
                    valor = float(sub.loc[pos, "monto"])
                    z_ref = (
                        z_modificado(valor, mediana, mad)
                        if not sin_dispersion
                        else desvio_relativo(valor, mediana)
                    )
                    encontrados.append(
                        (movimientos[pos], float(puntuaciones[i]), severidad_de(z_ref))
                    )
        elif sin_dispersion:
            # ---- Sin dispersión observada: se gradúa por desvío relativo ----
            # (con la mediana exacta, el Z modificado sería infinito para
            # cualquier desvío: no distinguiría €460 de €50000).
            metodos.add("Z modificado (MAD)")
            for pos in sub.index:
                valor = float(sub.loc[pos, "monto"])
                rel = desvio_relativo(valor, mediana)
                if rel >= UMBRAL_DESVIO_RELATIVO:
                    punt = round(min(rel * 100.0, TOPE_PUNTUACION), 2)
                    encontrados.append((movimientos[pos], punt, severidad_de(rel * 100.0)))
        else:
            # ---- Z-score modificado (robusto ante outliers y ruido) ----
            metodos.add("Z modificado (MAD)")
            for pos in sub.index:
                valor = float(sub.loc[pos, "monto"])
                z_mod = z_modificado(valor, mediana, mad)
                if z_mod >= UMBRAL_Z_MODIFICADO:
                    # `inf` (MAD == 0) se topa: JSON no admite infinitos.
                    punt = round(min(z_mod, TOPE_PUNTUACION), 2)
                    encontrados.append((movimientos[pos], punt, severidad_de(z_mod)))

    # Las puntuaciones de ambos métodos no son comparables entre sí, pero sí
    # ordenan dentro de cada método: se ordena de mayor a menor y se recorta.
    encontrados.sort(key=lambda trio: trio[1], reverse=True)
    items = [
        AnomaliaOut(
            id=m["id"],
            fecha=m["fecha"],
            descripcion=m["descripcion"] or None,
            tipo=m["tipo"],
            monto=m["monto"],
            categoria=m["categoria"],
            metodo_pago=m["metodo_pago"],
            puntuacion=round(puntuacion, 2),
            severidad=severidad,
        )
        for m, puntuacion, severidad in encontrados[:MAX_ANOMALIAS]
    ]

    metodo_txt = " y ".join(sorted(metodos)) if metodos else None
    umbral_txt = (
        f"IsolationForest: contaminación {CONTAMINACION_IF:.0%} por tipo "
        f"(≥{MIN_MUESTRAS_IF} muestras); Z modificado (MAD): ≥ {UMBRAL_Z_MODIFICADO} "
        f"({MIN_MUESTRAS_ANALISIS}-{MIN_MUESTRAS_IF - 1} muestras; "
        f"sin dispersión: desvío ≥ {UMBRAL_DESVIO_RELATIVO:.0%})."
        if metodos
        else None
    )

    return AnomaliasOut(
        disponible=True,
        metodo=metodo_txt,
        umbral=umbral_txt,
        total_analizados=total,
        items=items,
        mensaje=None if items else "No se detectaron movimientos inusuales. ¡Buen control!",
    )
