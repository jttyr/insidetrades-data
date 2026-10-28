"""Cálculo de α rodante vía regresión diaria contra un benchmark.

Modelo: r_asset_t = α + β · r_bench_t + ε_t

- α rodante: intercepto de la regresión OLS sobre la ventana de las
  últimas N sesiones. Se anualiza multiplicando por TRADING_DAYS.
- β rodante: pendiente de esa misma regresión.
- Residuos ε: lo que el activo entregó por encima de lo que la beta
  habría predicho. Su acumulado es la medida honesta del edge.
- Information Ratio: α / σ(ε), estandariza el edge por su propio ruido.
"""

import numpy as np
import pandas as pd

import config
import data


def _ols(y: np.ndarray, x: np.ndarray) -> tuple:
    """Regresión y = α + β·x por mínimos cuadrados.

    Devuelve (α, β, residuos). Hecho a mano con numpy para evitar la
    dependencia de statsmodels; la ventana es pequeña y numpy sobra.
    """
    x_mean = x.mean()
    y_mean = y.mean()
    var_x = ((x - x_mean) ** 2).sum()
    if var_x == 0:
        return float("nan"), float("nan"), np.full_like(y, np.nan)
    beta = ((x - x_mean) * (y - y_mean)).sum() / var_x
    alpha = y_mean - beta * x_mean
    residuals = y - (alpha + beta * x)
    return float(alpha), float(beta), residuals


def rolling_alpha(returns_asset: pd.Series, returns_bench: pd.Series,
                  window: int = None) -> pd.DataFrame:
    """α, β y residuo diario para cada fecha, con ventana rodante.

    Devuelve un DataFrame indexado por fecha con columnas:
      alpha_annual  - α de la regresión anualizada (×TRADING_DAYS)
      beta          - β de la regresión
      residual      - residuo del ÚLTIMO día de la ventana (ε_t)

    El residuo del último día se expone aparte porque al acumularlo
    reconstruye el α "entregado" en vez del α "ajustado": es la curva
    que la gente de mesa quiere ver, no el intercepto en sí.
    """
    window = window or config.WINDOW
    asset_ret, bench_ret = data.align(returns_asset, returns_bench)

    if len(asset_ret) < window:
        return pd.DataFrame(columns=["alpha_annual", "beta", "residual"])

    rows = []
    for i in range(window - 1, len(asset_ret)):
        y = asset_ret.iloc[i - window + 1: i + 1].to_numpy()
        x = bench_ret.iloc[i - window + 1: i + 1].to_numpy()
        alpha, beta, resid = _ols(y, x)
        rows.append({
            "date": asset_ret.index[i],
            "alpha_annual": alpha * config.TRADING_DAYS,
            "beta": beta,
            "residual": float(resid[-1]),
        })
    return pd.DataFrame(rows).set_index("date")


def information_ratio(residuals: pd.Series) -> float:
    """IR = media(ε) / std(ε), anualizado.

    Mide el edge por unidad de ruido residual: mejor que α a secas
    porque descuenta la variabilidad del residuo. IR > 0.5 ya es
    consistente, > 1.0 es excepcional.
    """
    clean = residuals.dropna()
    if len(clean) < 2 or clean.std() == 0:
        return float("nan")
    return float(clean.mean() / clean.std() * np.sqrt(config.TRADING_DAYS))


def r_squared(returns_asset: pd.Series, returns_bench: pd.Series,
              window: int = None) -> float:
    """R² de la última ventana. Qué tan bien el benchmark explica al
    activo: < 0.5 significa que α y β son ruidosos y no se les debe hacer
    mucho caso."""
    window = window or config.WINDOW
    asset_ret, bench_ret = data.align(returns_asset, returns_bench)
    if len(asset_ret) < window:
        return float("nan")
    y = asset_ret.iloc[-window:].to_numpy()
    x = bench_ret.iloc[-window:].to_numpy()
    _, _, resid = _ols(y, x)
    ss_res = (resid ** 2).sum()
    ss_tot = ((y - y.mean()) ** 2).sum()
    if ss_tot == 0:
        return float("nan")
    return float(1.0 - ss_res / ss_tot)


def monthly_alpha(residuals: pd.Series) -> pd.Series:
    """α mensual (puntos porcentuales) a partir de los residuos diarios.

    Se suman los residuos del mes y se multiplican por 100 para pasar a
    puntos porcentuales. No se anualiza: lo que se quiere ver es cuánto
    α entregó ESE MES en concreto.
    """
    clean = residuals.dropna()
    if clean.empty:
        return pd.Series(dtype=float)
    monthly = clean.groupby(pd.Grouper(freq="ME")).sum() * 100
    return monthly


def analyze_symbol(symbol: str) -> dict:
    """Pipeline completo para un activo.

    Devuelve un dict con todo lo que el dashboard necesita, o None si
    algún dato esencial falta.
    """
    bench_symbol = config.BENCHMARKS[symbol]
    asset_closes = data.get_closes(symbol)
    bench_closes = data.get_closes(bench_symbol)

    if asset_closes.empty or bench_closes.empty:
        print(f"[{symbol}] sin datos de precio, se omite.")
        return None

    asset_ret = asset_closes.pct_change().dropna()
    bench_ret = bench_closes.pct_change().dropna()

    rolling = rolling_alpha(asset_ret, bench_ret)
    if rolling.empty:
        print(f"[{symbol}] ventana insuficiente, se omite.")
        return None

    # Alpha acumulada: suma de residuos × 100 para pct. Se anualiza por
    # separado para la etiqueta "α acumulada 1y".
    cum_alpha = rolling["residual"].cumsum() * 100

    last = rolling.iloc[-1]
    ir = information_ratio(rolling["residual"])
    r2 = r_squared(asset_ret, bench_ret)

    # Percentil 1y del α actual contra su propia serie rodante.
    alpha_series = rolling["alpha_annual"]
    percentile = float((alpha_series < last["alpha_annual"]).mean() * 100)

    # Momentum temporal: α de hoy vs α de hace N días. Permite ver si el
    # edge está acelerando o desinflando -- lo que el usuario necesita para
    # tradear hoy.
    def _lookback(days):
        if len(alpha_series) < days + 1:
            return float("nan")
        return float(alpha_series.iloc[-1 - days] * 100)

    momentum = {
        "ahora": alpha_series.iloc[-1] * 100,
        "ayer": _lookback(1),
        "hace_5d": _lookback(5),
        "hace_20d": _lookback(20),
        "hace_60d": _lookback(60) if len(alpha_series) >= 61 else float("nan"),
    }

    # Distribución realizada de α a 60d: sliding sum de residuos. Es la
    # historia de "qué α entregaba el activo en ventanas de 60 días": la
    # usamos para dibujar la densidad del PASADO en el ridge.
    sliding_60 = (rolling["residual"].rolling(60).sum() * 100).dropna()

    return {
        "symbol": symbol,
        "label": config.LABELS.get(symbol, symbol),
        "benchmark": bench_symbol,
        "alpha_annual_pct": last["alpha_annual"] * 100,
        "beta": last["beta"],
        "r_squared": r2,
        "info_ratio": ir,
        "cum_alpha_pct": float(cum_alpha.iloc[-1]),
        "percentile_1y": percentile,
        "alpha_series_pct": alpha_series * 100,
        "cum_alpha_curve": cum_alpha,
        "monthly_alpha": monthly_alpha(rolling["residual"]),
        "residuals": rolling["residual"],
        "realized_60d_distribution": sliding_60,
        "momentum": momentum,
    }
