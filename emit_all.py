"""Genera en data/ los CSV que el EA descarga por WebRequest (regime, alpha, market drivers). Corre en GitHub Actions."""
import os, sys, runpy
ROOT = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(ROOT, "data"); os.makedirs(OUT, exist_ok=True)
sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, "alpha_terminal"))
import pathlib
import emit_market_regime_csv as reg
reg.MT5_FILES_PATH = pathlib.Path(OUT); reg.main()
import emit_alpha_csv as al
al.MT5_FILES = OUT; al.HIST = os.path.join(OUT, "history"); al.run("QQQ")
import emit_drivers_csv as dr
dr.MT5_FILES = OUT; dr.HIST = os.path.join(OUT, "history")
import csv, datetime as dt
o = dr.run(); hdr = ["ts"] + list(o); row = [dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")] + [round(v, 4) for v in o.values()]
with open(os.path.join(OUT, "market_drivers_latest.csv"), "w", newline="") as f:
    w = csv.writer(f); w.writerow(hdr); w.writerow(row)
print("OK", os.listdir(OUT))
