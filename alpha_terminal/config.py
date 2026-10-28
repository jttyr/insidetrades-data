"""Configuración del Alpha Terminal.

Complementa al GEX terminal: donde el GEX dice DÓNDE actúa el precio,
este dice QUIÉN está entregando edge contra su benchmark después de
descontar beta.
"""

import datetime as dt
import os
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

load_dotenv()

# Mismo universo del GEX terminal (los activos con mercado de opciones):
# así los dos tableros hablan de los mismos instrumentos.
UNIVERSE = ["QQQ", "SPY", "DIA", "GLD", "USO"]

# Nombres cortos para la leyenda del dashboard. Convención de mesa: QQQ,
# SPY, DJI/DIA, GLD, USO.
LABELS = {
    "SPY": "SPY", "QQQ": "QQQ", "DIA": "DIA",
    "GLD": "GLD", "USO": "USO",
}

NAMES = {
    "SPY": "SPDR S&P 500 ETF",
    "QQQ": "Invesco QQQ Trust",
    "DIA": "SPDR Dow Jones ETF",
    "GLD": "SPDR Gold Shares",
    "USO": "United States Oil Fund",
}

# Benchmark por activo. La regla es que el benchmark sea un paso más amplio
# que el activo dentro de SU MISMO factor: así la α mide el premio del tilt
# y no una diferencia de factor que la regresión no sabe interpretar.
#
# - SPY vs sí mismo daría α=0 por construcción: se cambia por ACWI (mundo),
#   que mide si EE.UU. bate al mercado global.
# - QQQ/DIA vs SPY: mismo factor equity, mide el premio del tilt tech o
#   industrial dentro del S&P.
# - GLD/USO vs DBC (canasta broad commodities): equities como benchmark de
#   oro o petróleo meten beta de equity y rompen la lectura (R² se desploma
#   y la α se vuelve ruido). DBC comparte factor commodity y da α interpretable.
BENCHMARKS = {
    "SPY": "ACWI",
    "QQQ": "SPY",
    "DIA": "SPY",
    "GLD": "DBC",
    "USO": "DBC",
}

# Ventana de regresión rodante (sesiones). 60 es el estándar en la mesa:
# suficiente para que β sea estable, corto para captar cambios de régimen.
WINDOW = 60

# Período total que se descarga y se grafica.
HISTORY_DAYS = 400          # buffer: 252 sesiones + warmup del rolling

# Días en un año de trading, para anualizar α y volatilidad.
TRADING_DAYS = 252

# --- Zona horaria y agenda ---
# El dashboard se dispara post-cierre (16:00 ET = 15:00 MX inv / 14:00 MX ver).
MARKET_TZ = "America/New_York"
LOCAL_TZ = "America/Mexico_City"


def now_local() -> dt.datetime:
    return dt.datetime.now(ZoneInfo(LOCAL_TZ))


# --- Salida ---
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# --- Discord (opcional, mismo patrón que el GEX) ---
DISCORD_WEBHOOK_ALPHA = os.getenv("DISCORD_WEBHOOK_ALPHA", "").strip()

# --- Modo de prueba ---
DRY_RUN = os.getenv("DRY_RUN", "false").strip().lower() == "true"
