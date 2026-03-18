import json
import os
from datetime import time as dt_time

# Load MCX instruments from JSON (includes tokens and margin requirements)
_config_dir = os.path.dirname(os.path.abspath(__file__))
_instruments_path = os.path.join(_config_dir, 'mcx_instruments.json')

try:
    with open(_instruments_path) as f:
        _instruments_data = json.load(f)
        MCX_INSTRUMENTS = _instruments_data.get('instruments', [])
except Exception:
    MCX_INSTRUMENTS = []

# Build SYMBOLS_UNIVERSE from instruments
SYMBOLS_UNIVERSE = [inst['symbol'] for inst in MCX_INSTRUMENTS]

# Build SYMBOLS_FUTURE_UNIVERSE with proper MCX|token format
SYMBOLS_FUTURE_UNIVERSE = [f"MCX|{inst['token']}" for inst in MCX_INSTRUMENTS]

MARKET_OPEN = dt_time(9, 0)
MARKET_CLOSE = dt_time(23, 30)
OPTION_INSTRUMENT = 'OPTFUT'
MAX_NOMINAL_PRICE = 500000

# 🔥 COMMODITY VOLATILITY ADJUSTMENTS (v3.14.0)
SL_MULT_TRENDING = 2.0
SL_MULT_SIDEWAYS = 0.35

# Load MCX Holidays
_orbiter_root = os.path.dirname(os.path.dirname(os.path.dirname(_config_dir)))
_holidays_path = os.path.join(_orbiter_root, 'data', 'mcx', 'holidays.json')
try:
    with open(_holidays_path) as f:
        _holidays_data = json.load(f)
        MARKET_HOLIDAYS = _holidays_data.get("2026", [])
except Exception:
    MARKET_HOLIDAYS = []

# Helper to get margin for a symbol
def get_mcx_margin(symbol: str) -> float:
    """Get required margin for 1 lot of MCX instrument."""
    for inst in MCX_INSTRUMENTS:
        if inst['symbol'].upper() == symbol.upper():
            return inst.get('margin_per_lot', 0)
    return 0

def get_mcx_lot_size(symbol: str) -> int:
    """Get lot size for MCX instrument."""
    for inst in MCX_INSTRUMENTS:
        if inst['symbol'].upper() == symbol.upper():
            return inst.get('lot_size', 1)
    return 1
