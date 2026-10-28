"""Emite alpha_qqq_latest.csv (para el EA de MT5) + historial diario.
Columnas: ts, alpha_annual_pct, beta, info_ratio, percentile_1y, mom_1d, mom_5d, mom_20d, alpha_sign
alpha_sign = +1 si el alpha de hoy supera al de hace 5 dias y es positivo, -1 si es negativo y cae, 0 en otro caso.
"""
import csv, os, sys
from datetime import datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import alpha

MT5_FILES = ("/Users/jaimetopete/Library/Application Support/net.metaquotes.wine.metatrader5/"
             "drive_c/Program Files/MetaTrader 5/MQL5/Files")
HIST = os.path.join(os.path.dirname(os.path.abspath(__file__)), "alpha_history")

def run(symbol="QQQ"):
    r = alpha.analyze_symbol(symbol)
    m = r["momentum"]
    a = r["alpha_annual_pct"]
    sign = 1 if (a > 0 and m["ahora"] >= m["hace_5d"]) else (-1 if (a < 0 and m["ahora"] <= m["hace_5d"]) else 0)
    hdr = ["ts", "alpha_annual_pct", "beta", "info_ratio", "percentile_1y", "mom_1d", "mom_5d", "mom_20d", "alpha_sign"]
    row = [datetime.now().strftime("%Y-%m-%d %H:%M:%S"), round(a, 4), round(r["beta"], 4), round(r["info_ratio"], 4),
           round(r["percentile_1y"], 1), round(m["ahora"] - m["ayer"], 4), round(m["ahora"] - m["hace_5d"], 4),
           round(m["ahora"] - m["hace_20d"], 4), sign]
    os.makedirs(HIST, exist_ok=True)
    hp = os.path.join(HIST, f"alpha_{symbol}.csv")          # un archivo acumulativo
    new = not os.path.exists(hp)
    with open(hp, "a", newline="") as f:
        w = csv.writer(f)
        if new: w.writerow(hdr)
        w.writerow(row)
    if os.path.isdir(MT5_FILES):
        with open(os.path.join(MT5_FILES, f"alpha_{symbol.lower()}_latest.csv"), "w", newline="") as f:
            w = csv.writer(f); w.writerow(hdr); w.writerow(row)
    return hdr, row

if __name__ == "__main__":
    h, r = run("QQQ"); print(dict(zip(h, r)))
