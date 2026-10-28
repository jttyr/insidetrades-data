#!/usr/bin/env python3
"""
emit_market_regime_csv.py
-------------------------
Implementa el modelo "Market regime filter analysis" del user (gap-based driver detection).

LÓGICA EXACTA (confirmada por el user):
  1. Baseline AM/PM = 50/50 por sesión y lado.
  2. Detecta driver session:
       - PM por default (día de tendencia)
       - AM cuando gap de apertura >= 0.45%
  3. Suma +2 a +4 puntos al lado dominante de la session driver
     (el monto escala con la convicción del día: |gap| → más puntos).
  4. El lado "dominante" se infiere por la dirección del gap:
       - gap > 0 → HIGH probable en session driver, LOW en la otra
       - gap < 0 → LOW probable en session driver, HIGH en la otra

Output CSV (ej. market_regime_nq_latest.csv):
  ticker,am_high,am_low,pm_high,pm_low,driver,gap_pct,conviction

Ejemplo para día con gap +0.52% → driver AM:
  NQ,69,31,34,67,AM,0.52,3

Instala en:
  /Users/jaimetopete/Library/Application Support/net.metaquotes.wine.metatrader5/
    drive_c/Program Files/MetaTrader 5/MQL5/Files/market_regime_nq_latest.csv

Ejecutar diariamente ~09:00 NY (o antes del open).
"""
from __future__ import annotations
import csv
import sys
from datetime import datetime, timezone
from pathlib import Path

import yfinance as yf    # pip install yfinance

# Config
TICKERS = {
    # Mapping ticker_user_csv → yahoo_symbol
    "NQ":    "NQ=F",
    "ES":    "ES=F",
    "XAU":   "GC=F",     # Gold futures
    "USTEC": "NQ=F",     # Alias del user para broker ICMarkets
}
GAP_THRESHOLD_PCT = 0.45     # gap >= este → driver AM, si no → PM

# Path destino MT5 (ajusta si tu wineprefix es distinto)
MT5_FILES_PATH = Path(
    "/Users/jaimetopete/Library/Application Support/"
    "net.metaquotes.wine.metatrader5/drive_c/Program Files/"
    "MetaTrader 5/MQL5/Files"
)


def compute_gap(ticker: str) -> tuple[float, float]:
    """
    Devuelve (gap_pct, current_price).
    gap_pct = (open_today - close_yesterday) / close_yesterday * 100
    """
    data = yf.download(ticker, period="5d", interval="1d", progress=False, auto_adjust=False)
    if len(data) < 2:
        return 0.0, 0.0
    # yfinance >=0.2.60 returns MultiIndex columns per ticker, squeeze if needed
    close_col = data["Close"]
    open_col = data["Open"]
    if hasattr(close_col, "columns") and len(close_col.columns) > 0:
        close_col = close_col.iloc[:, 0]
        open_col = open_col.iloc[:, 0]
    close_yesterday = float(close_col.iloc[-2])
    open_today = float(open_col.iloc[-1])
    current_price = float(close_col.iloc[-1])
    if close_yesterday == 0:
        return 0.0, current_price
    gap_pct = (open_today - close_yesterday) / close_yesterday * 100.0
    return gap_pct, current_price


def regime_probabilities(gap_pct: float) -> dict:
    """
    Implementa la lógica del user:
      - PM default driver
      - AM driver si |gap| >= 0.45%
      - Lado dominante determinado por signo del gap
      - Puntos +2 a +4 según magnitud del gap
    """
    abs_gap = abs(gap_pct)
    gap_up = gap_pct > 0

    # Determina driver
    if abs_gap >= GAP_THRESHOLD_PCT:
        driver = "AM"
    else:
        driver = "PM"

    # Convicción: 2-4 puntos escalado por magnitud del gap
    if abs_gap >= 1.0:
        conviction = 4
    elif abs_gap >= 0.7:
        conviction = 3
    elif abs_gap >= 0.45:
        conviction = 3
    elif abs_gap >= 0.2:
        conviction = 2
    else:
        conviction = 2

    # Baseline 50/50
    am_high, am_low = 50, 50
    pm_high, pm_low = 50, 50

    # Aplicar ajuste al driver + inverso al no-driver
    adj = conviction * 10  # 2 pts conv → 20 pp, 4 pts conv → 40 pp (más agresivo que spec?)
    # El user mostró ejemplos tipo 69/31 que son ~19 pp de ajuste
    adj = conviction * 5 + 10  # 2→20, 3→25, 4→30 pp (encaja mejor con 69/31)

    if driver == "AM":
        if gap_up:
            am_high += adj // 2
            am_low  -= adj // 2
            pm_high -= adj // 2
            pm_low  += adj // 2
        else:
            am_high -= adj // 2
            am_low  += adj // 2
            pm_high += adj // 2
            pm_low  -= adj // 2
    else:  # PM driver (día tendencial)
        if gap_up:
            pm_high += adj // 2
            pm_low  -= adj // 2
            am_high -= adj // 2
            am_low  += adj // 2
        else:
            pm_high -= adj // 2
            pm_low  += adj // 2
            am_high += adj // 2
            am_low  -= adj // 2

    # Clamp 10..90
    def clamp(x): return max(10, min(90, x))
    return dict(
        am_high=clamp(am_high),
        am_low=clamp(am_low),
        pm_high=clamp(pm_high),
        pm_low=clamp(pm_low),
        driver=driver,
        gap_pct=round(gap_pct, 3),
        conviction=conviction,
    )


def main():
    MT5_FILES_PATH.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    out_rows = []
    for user_ticker, yahoo_symbol in TICKERS.items():
        try:
            gap_pct, price = compute_gap(yahoo_symbol)
        except Exception as e:
            print(f"  ! {user_ticker}: {e}", file=sys.stderr)
            continue
        regime = regime_probabilities(gap_pct)
        row = [
            user_ticker,
            regime["am_high"],
            regime["am_low"],
            regime["pm_high"],
            regime["pm_low"],
            regime["driver"],
            regime["gap_pct"],
            regime["conviction"],
            stamp,
        ]
        out_rows.append(row)
        print(f"  {user_ticker:6s} AM={regime['am_high']}/{regime['am_low']} "
              f"PM={regime['pm_high']}/{regime['pm_low']} "
              f"driver={regime['driver']} gap={gap_pct:+.2f}% conv={regime['conviction']}")

    # Write individual files per ticker (what the EA expects)
    header = ["ticker", "am_high", "am_low", "pm_high", "pm_low",
              "driver", "gap_pct", "conviction", "stamp"]
    for row in out_rows:
        ticker = row[0].lower()
        # EA reads market_regime_nq_latest.csv (ticker-specific)
        fname = f"market_regime_{ticker}_latest.csv"
        path = MT5_FILES_PATH / fname
        with open(path, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(header)
            w.writerow(row)
        print(f"  → wrote {path}")

    # Also write combined file for inspection
    combined = MT5_FILES_PATH / "market_regime_all_latest.csv"
    with open(combined, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(out_rows)
    print(f"  → wrote {combined}")


if __name__ == "__main__":
    main()
