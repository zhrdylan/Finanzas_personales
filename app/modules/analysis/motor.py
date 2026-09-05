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
UMBRAL_ZSCORE = 3.0  # |z| >= 3 se considera anómalo
MIN_MUESTRAS_ANALISIS = 10  # mínimo global para intentar el análisis
MIN_MUESTRAS_IF = 30  # mínimo por tipo para usar IsolationForest
CONTAMINACION_IF = 0.05  # proporción esperada de anomalías
MAX_ANOMALIAS = 10  # límite de resultados devueltos
TOLERANCIA_TENDENCIA = 0.05  # pendiente relativa ±5% => "estable"


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
    - Con 10 a 29 muestras:  z-score (|z| >= 3).
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

    encontrados: list[tuple[dict, float]] = []
    metodos: set[str] = set()

    for tipo in ("gasto", "ingreso"):
        sub = df[df["tipo"] == tipo]
        if len(sub) < MIN_MUESTRAS_ANALISIS:
            continue  # pocas muestras de este tipo: no se analiza

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
                    encontrados.append((movimientos[pos], float(puntuaciones[i])))
        else:
            # ---- Z-score (estadístico clásico) ----
            metodos.add("Z-score")
            media = float(sub["monto"].mean())
            desviacion = float(sub["monto"].std(ddof=0))
            if desviacion > 0:
                z = ((sub["monto"] - media) / desviacion).abs()
                for pos in z[z >= UMBRAL_ZSCORE].index:
                    encontrados.append((movimientos[pos], float(z[pos])))

    # Las puntuaciones de ambos métodos no son comparables entre sí, pero sí
    # ordenan dentro de cada método: se ordena de mayor a menor y se recorta.
    encontrados.sort(key=lambda par: par[1], reverse=True)
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
        )
        for m, puntuacion in encontrados[:MAX_ANOMALIAS]
    ]

    metodo_txt = " y ".join(sorted(metodos)) if metodos else None
    umbral_txt = (
        f"IsolationForest: contaminación {CONTAMINACION_IF:.0%} por tipo "
        f"(≥{MIN_MUESTRAS_IF} muestras); Z-score: |z| ≥ {UMBRAL_ZSCORE:.0f} "
        f"({MIN_MUESTRAS_ANALISIS}-{MIN_MUESTRAS_IF - 1} muestras)."
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
