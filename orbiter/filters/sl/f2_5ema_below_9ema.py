import numpy as np
import talib
from orbiter.utils.utils import safe_float

def sl_5ema_below_9ema(position, ltp, data):
    """
    🎯 SL: EMA REVERSAL
    Triggers exit if EMA5 crosses below EMA9 (for Longs) 
    or EMA5 crosses above EMA9 (for Shorts).
    """
    candle_data = data.get('candles', []) if data else []
    if not candle_data or len(candle_data) < 15:
        return {'hit': False}

    # 1. Prepare Closes
    closes = np.array([safe_float(c['intc']) for c in candle_data if c.get('stat')=='Ok'], dtype=float)
    if len(closes) < 10:
        return {'hit': False}

    # 2. Calculate EMAs (using validated Metastock compatibility)
    try:
        talib.set_compatibility(1)
        ema5 = talib.EMA(closes, timeperiod=5)
        ema9 = talib.EMA(closes, timeperiod=9)
    finally:
        talib.set_compatibility(0)

    latest_ema5 = ema5[-1]
    latest_ema9 = ema9[-1]
    
    strategy = position.get('strategy', 'PUT_CREDIT_SPREAD')
    
    # 3. Logic: Exit if EMAs disagree with the trade direction
    if strategy == 'PUT_CREDIT_SPREAD': # Bullish Trade
        if latest_ema5 < latest_ema9:
            return {'hit': True, 'reason': 'SL: EMA5 < EMA9 (Bullish Reversal)'}
    else: # Bearish Trade (CALL_CREDIT_SPREAD)
        if latest_ema5 > latest_ema9:
            return {'hit': True, 'reason': 'SL: EMA5 > EMA9 (Bearish Reversal)'}

    return {'hit': False}
