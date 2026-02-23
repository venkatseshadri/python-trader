import numpy as np
from config.config import VERBOSE_LOGS
from utils.utils import safe_float

def institutional_flip_filter(data, candle_data, **kwargs):
    """
    🎯 F9: INSTITUTIONAL FLIP & LEVEL BREAKER
    Logic: Detects if yesterday's levels (High/Low) are being tested or flipped.
    Patterns: BULL_FLIP, BEAR_FLIP, YHIGH_BREAK, YLOW_BREAK.
    """
    token = kwargs.get('token')
    
    ltp = safe_float(data.get('lp', 0))
    yest_high = safe_float(data.get('ph', 0)) # Previous High
    yest_low = safe_float(data.get('pl', 0))  # Previous Low
    yest_close = safe_float(data.get('pc', 0)) # Previous Close
    yest_open = safe_float(data.get('po', 0))  # Previous Open (Custom added to SYMBOLDICT usually)
    
    if ltp == 0 or yest_high == 0 or yest_low == 0:
        return {'score': 0.00}

    # Identify Yesterday's Color
    yest_color = "Green" if yest_close > yest_open else "Red"
    
    # Get Today's Session High/Low from candles
    if not candle_data:
        return {'score': 0.00}
    highs = [safe_float(c.get('inth')) for c in candle_data if c.get('stat')=='Ok']
    day_high = max(highs) if highs else 0
    day_low = min([safe_float(c.get('intl')) for c in candle_data if c.get('stat')=='Ok']) if highs else 0

    score = 0.00
    pattern = "NONE"

    # --- 1. BULL_FLIP: Yesterday Red + Low < YHigh + LTP > YHigh ---
    if yest_color == "Red" and day_low < yest_high and ltp > yest_high:
        score = 0.50
        pattern = "BULL_FLIP"
    
    # --- 2. BEAR_FLIP: Yesterday Green + High > YLow + LTP < YLow ---
    elif yest_color == "Green" and day_high > yest_low and ltp < yest_low:
        score = -0.50
        pattern = "BEAR_FLIP"
        
    # --- 3. Simple Level Breaks (Fallback) ---
    elif ltp > yest_high:
        score = 0.25
        pattern = "YHIGH_BREAK"
    elif ltp < yest_low:
        score = -0.25
        pattern = "YLOW_BREAK"

    if VERBOSE_LOGS and pattern != "NONE":
        print(f"🏦 F9_FLIP {token}: Pattern={pattern} LTP={ltp:.2f} YH={yest_high:.2f} YL={yest_low:.2f} Score={score:>+5.2f}")

    return {
        'score': score,
        'pattern': pattern
    }
