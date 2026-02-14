import numpy as np
from filters.entry.f4_supertrend import calculate_st_values
from utils.utils import safe_float

def sl_supertrend_reversal(position, ltp, data):
    """
    🎯 SL: SUPERTREND FLIP
    Triggers exit if SuperTrend flips against the trade direction.
    """
    candle_data = data.get('candles', []) if data else []
    if not candle_data or len(candle_data) < 20:
        return {'hit': False}

    # 1. Prepare Data
    highs = np.array([safe_float(c['inth']) for c in candle_data if c.get('stat')=='Ok'], dtype=float)
    lows = np.array([safe_float(c['intl']) for c in candle_data if c.get('stat')=='Ok'], dtype=float)
    closes = np.array([safe_float(c['intc']) for c in candle_data if c.get('stat')=='Ok'], dtype=float)

    if len(closes) < 20:
        return {'hit': False}

    # 2. Calculate ST
    # Period 10, Multiplier 3 (Standard)
    st_series = calculate_st_values(highs, lows, closes, 10, 3.0)
    latest_st = st_series[-1]
    
    strategy = position.get('strategy', 'PUT_CREDIT_SPREAD')

    # 3. Logic: Exit on Flip
    if strategy == 'PUT_CREDIT_SPREAD': # Bullish Trade
        if ltp < latest_st:
            return {'hit': True, 'reason': 'SL: SuperTrend Flipped (BEAR)'}
    else: # Bearish Trade
        if ltp > latest_st:
            return {'hit': True, 'reason': 'SL: SuperTrend Flipped (BULL)'}

    return {'hit': False}
