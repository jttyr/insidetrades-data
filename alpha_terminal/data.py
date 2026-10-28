"""Precios diarios ajustados. Fuente: Yahoo via yfinance.

Devuelve una Series de precios de cierre ajustado (dividendos y splits
reinvertidos). El cierre ajustado es el correcto para medir α: el α de
GLD sin reinvertir dividendos subestima el edge, y en el S&P sin ajustar
es imposible comparar años con payouts distintos.
"""

import datetime as dt
import pandas as pd
import yfinance as yf

import config


def get_closes(symbol: str, days: int = None) -> pd.Series:
    """Serie de cierres ajustados de los últimos `days` días naturales.

    Devuelve una Series indexada por fecha, sin huecos (sólo días de
    sesión). Si Yahoo no entrega el símbolo o la respuesta llega vacía,
    devuelve una Series vacía -- el llamador decide qué hacer.
    """
    days = days or config.HISTORY_DAYS
    end = dt.date.today()
    # Se pide margen extra para absorber feriados, fines de semana y
    # cualquier barra que yfinance decida borrar: al final se recorta.
    start = end - dt.timedelta(days=int(days * 1.6))

    try:
        df = yf.download(
            symbol,
            start=start.isoformat(),
            end=(end + dt.timedelta(days=1)).isoformat(),
            progress=False,
            auto_adjust=True,
            threads=False,
        )
    except Exception as exc:
        print(f"[{symbol}] yfinance error: {exc!r}")
        return pd.Series(dtype=float)

    if df is None or df.empty:
        return pd.Series(dtype=float)

    # yfinance puede devolver un MultiIndex en columnas cuando se pide un
    # solo ticker; se aplana.
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    closes = df["Close"].dropna()
    closes.name = symbol

    # Normaliza el índice a fechas sin timezone (comparar fechas, no
    # timestamps, al cruzar varios símbolos).
    closes.index = pd.to_datetime(closes.index).tz_localize(None).normalize()
    return closes.tail(days)


def align(series_a: pd.Series, series_b: pd.Series) -> tuple:
    """Dos series alineadas a su índice común (inner join).

    Es necesario antes de calcular retornos conjuntos: si una serie tiene
    un día que la otra no, el retorno de ese día queda mal pareado y
    contamina la regresión.
    """
    df = pd.concat([series_a, series_b], axis=1, join="inner").dropna()
    return df.iloc[:, 0], df.iloc[:, 1]
