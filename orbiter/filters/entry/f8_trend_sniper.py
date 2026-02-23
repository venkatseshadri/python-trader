import numpy as np
import talib
from config.config import VERBOSE_LOGS
from utils.utils import safe_float

def trend_sniper_filter(data, candle_data, **kwargs):
    """
    🎯 F8: TREND SNIPER (ADX + EMA COMBO)
    Logic: Requires ADX > 25 for trend strength AND EMA5/9 alignment.
    This acts as a high-quality gatekeeper for multi-stock execution.
    """
    token = kwargs.get('token')
    
    if not candle_data or len(candle_data) < 30:
        return {'score': 0.00}

    highs = np.array([safe_float(c['inth']) for c in candle_data if c.get('stat')=='Ok'], dtype=float)
    lows = np.array([safe_float(c['intl']) for c in candle_data if c.get('stat')=='Ok'], dtype=float)
    closes = np.array([safe_float(c['intc']) for c in candle_data if c.get('stat')=='Ok'], dtype=float)

    if len(closes) < 30:
        return {'score': 0.00}

    # 1. Calculate ADX(14)
    adx_vals = talib.ADX(highs, lows, closes, timeperiod=14)
    current_adx = adx_vals[-1] if not np.isnan(adx_vals[-1]) else 0.0
    
    # 2. Calculate EMA 5 & 9
    ema5 = talib.EMA(closes, timeperiod=5)
    ema9 = talib.EMA(closes, timeperiod=9)
    
    e5 = ema5[-1]
    e9 = ema9[-1]

    score = 0.00
    # 3. Sniper Logic (ADX > 25)
    if current_adx > 25:
        if e5 > e9:
            score = 0.25 # Confirmed Bullish
        elif e5 < e9:
            score = -0.25 # Confirmed Bearish
    
    if VERBOSE_LOGS:
        print(f"🎯 F8_SNIPER {token}: ADX={current_adx:.2f} E5={e5:.2f} E9={e9:.2f} F8={score:>+5.2f}")

    return {
        'score': score,
        'adx': round(current_adx, 2),
        'direction': 'BULL' if e5 > e9 else 'BEAR'
    }
