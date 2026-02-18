import json
import os
from datetime import time as dt_time

# Common MCX symbols including Minis and Micros (Corrected via API Discovery)
SYMBOLS_UNIVERSE = [
    'CRUDEOIL', 'CRUDEOILM', 'NATURALGAS', 
    'GOLD', 'GOLDM', 'GOLDPETAL', 
    'SILVER', 'SILVERM', 'SILVERMIC',
    'COPPER', 'ZINC', 'ZINCMINI', 'LEAD', 'LEADMINI', 'ALUMINIUM'
]

# This will be populated by update_mcx_config.py
SYMBOLS_FUTURE_UNIVERSE = [
    'MCX|467013', 'MCX|467014', 'MCX|467385', 'MCX|454818', 'MCX|472781',
    'MCX|472788', 'MCX|451666', 'MCX|451669', 'MCX|458305', 'MCX|477167',
    'MCX|477171', 'MCX|477172', 'MCX|477168', 'MCX|477169', 'MCX|477166'
]

MARKET_OPEN = dt_time(9, 0)
MARKET_CLOSE = dt_time(23, 30)
OPTION_INSTRUMENT = 'OPTFUT'

# 🔥 Load MCX Holidays from data/mcx/holidays.json
_base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_path = os.path.join(_base, 'data', 'mcx', 'holidays.json')
try:
    with open(_path) as f:
        _data = json.load(f)
        MARKET_HOLIDAYS = _data.get("2026", [])
except Exception:
    MARKET_HOLIDAYS = []
