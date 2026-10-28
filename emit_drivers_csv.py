"""Emite market_drivers_latest.csv (EA de MT5) + historial. Drivers de NASDAQ intradia:
US10Y (^TNX), VIX, DXY, Brent. Score de riesgo en [-1,1] (>0 = viento a favor de largos en NQ):
cada driver aporta -z(cambio 5d) por ser inverso al NASDAQ (yields, VIX, dolar suben = malo); Brent con peso menor.
"""
import csv, os, numpy as np
from datetime import datetime
import yfinance as yf

MT5_FILES = ("/Users/jaimetopete/Library/Application Support/net.metaquotes.wine.metatrader5/"
             "drive_c/Program Files/MetaTrader 5/MQL5/Files")
HIST = os.path.join(os.path.dirname(os.path.abspath(__file__)), "drivers_history")
SYMS = {"us10y": ("^TNX", 0.35), "vix": ("^VIX", 0.35), "dxy": ("DX-Y.NYB", 0.20), "brent": ("BZ=F", 0.10)}

def run():
    out = {}; score = 0.0
    for k, (sym, w) in SYMS.items():
        d = yf.download(sym, period="6mo", interval="1d", progress=False, auto_adjust=False)
        c = d["Close"]; c = c.iloc[:, 0] if hasattr(c, "columns") else c
        c = c.dropna(); ch5 = c.pct_change(5).dropna(); z = float((ch5.iloc[-1] - ch5.mean()) / (ch5.std() + 1e-9))
        out[k] = float(c.iloc[-1]); out[k + "_z5d"] = round(z, 3); out[k + "_chg1d"] = round(float(c.pct_change().iloc[-1]) * 100, 3)
        score += -w * float(np.clip(z, -2, 2)) / 2.0
    out["drivers_score"] = round(float(np.clip(score, -1, 1)), 3)
    return out

if __name__ == "__main__":
    o = run(); hdr = ["ts"] + list(o); row = [datetime.now().strftime("%Y-%m-%d %H:%M:%S")] + [round(v, 4) for v in o.values()]
    os.makedirs(HIST, exist_ok=True); hp = os.path.join(HIST, "drivers.csv"); new = not os.path.exists(hp)
    with open(hp, "a", newline="") as f:
        w = csv.writer(f)
        if new: w.writerow(hdr)
        w.writerow(row)
    if os.path.isdir(MT5_FILES):
        with open(os.path.join(MT5_FILES, "market_drivers_latest.csv"), "w", newline="") as f:
            w = csv.writer(f); w.writerow(hdr); w.writerow(row)
    print(dict(zip(hdr, row)))
