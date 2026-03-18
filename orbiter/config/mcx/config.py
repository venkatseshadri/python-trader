import json
import os
from datetime import time as dt_time

# Common MCX symbols including Minis and Micros (Corrected via API Discovery)
SYMBOLS_UNIVERSE = [
    'CRUDEOILM', 'NATGASMINI', 'NATURALGAS', 
    'GOLDPETAL', 
    'SILVERMIC',
    'COPPER', 'ZINCMINI', 'LEADMINI', 'ALUMINI', 'NICKEL'
]

# This will be populated by update_mcx_config.py
SYMBOLS_FUTURE_UNIVERSE = [
    'MCX|472790', 'MCX|475111', 'MCX|477175', 'MCX|466029',
    'MCX|487657', 'MCX|487663', 'MCX|487659', 'MCX|487655', 'MCX|487660'
]

MARKET_OPEN = dt_time(9, 0)
MARKET_CLOSE = dt_time(23, 30)
OPTION_INSTRUMENT = 'OPTFUT'
MAX_NOMINAL_PRICE = 500000 # Allow main Gold/Silver futures

# 🔥 COMMODITY VOLATILITY ADJUSTMENTS (v3.14.0)
SL_MULT_TRENDING = 2.0
SL_MULT_SIDEWAYS = 0.35

# 🔥 Load MCX Holidays from data/mcx/holidays.json
_base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_path = os.path.join(_base, 'data', 'mcx', 'holidays.json')
try:
    with open(_path) as f:
        _data = json.load(f)
        MARKET_HOLIDAYS = _data.get("2026", [])
except Exception:
    MARKET_HOLIDAYS = []
