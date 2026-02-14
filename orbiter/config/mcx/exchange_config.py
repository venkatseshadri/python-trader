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
    'MCX|467014',  # CRUDEOILM
    'MCX|467385',  # NATURALGAS
    'MCX|454818',  # GOLD
    'MCX|472781',  # GOLDM
    'MCX|472788',  # GOLDPETAL
    'MCX|451666',  # SILVER
    'MCX|451669',  # SILVERM
    'MCX|458305',  # SILVERMIC
    'MCX|477167',  # COPPER
    'MCX|477171',  # ZINC
    'MCX|477168',  # LEAD
    'MCX|477166',  # ALUMINIUM
] 

MARKET_OPEN = dt_time(17, 0)
MARKET_CLOSE = dt_time(23, 30)
OPTION_INSTRUMENT = 'OPTCOM'
EXECUTION_MODE = 'FUTURES'

# 🔥 ORB Window Parameters (Evening Session)
ORB_START_TIME = dt_time(17, 0)
ORB_END_TIME = dt_time(17, 15)

# 🔥 Load MCX Holidays from data/mcx/holidays.json
_base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_path = os.path.join(_base, 'data', 'mcx', 'holidays.json')
try:
    with open(_path) as f:
        _data = json.load(f)
        MARKET_HOLIDAYS = _data.get("2026", [])
except Exception:
    MARKET_HOLIDAYS = []
