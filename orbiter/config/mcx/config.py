import json
import os
from datetime import time as dt_time

# Common MCX symbols
SYMBOLS_UNIVERSE = [
    'CRUDEOIL', 'NATURALGAS', 'GOLD', 'SILVER', 'COPPER', 'ZINC', 'LEAD', 'ALUMINIUM'
]

# This will be populated by update_mcx_config.py
SYMBOLS_FUTURE_UNIVERSE = [
    'MCX|467013',  # CRUDEOIL
    'MCX|467385',  # NATURALGAS
    'MCX|454818',  # GOLD
    'MCX|451666',  # SILVER
    'MCX|477167',  # COPPER
    'MCX|477171',  # ZINC
    'MCX|477168',  # LEAD
    'MCX|477166',  # ALUMINIUM
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
