#!/usr/bin/env python3
"""
🚀 f3_5ema_above_9ema.py - FIXED ORB-STYLE SIMPLIFIED VERSION
(EMA5 - EMA9) / EMA5 × 100 = Raw %pts (NO ratio/cap, 2 decimals)
Drop-in replacement - F1/F2/F3 PERFECTLY consistent
"""

import talib
import numpy as np
from config.config import VERBOSE_LOGS
from utils.utils import safe_float

def ema5_above_9ema_filter(data, candle_data, token, weight=18):
    """
    🎯 F3_5EMA_ABOVE_9EMA SIMPLIFIED: (EMA5 - EMA9) / EMA5 × 100
    ORB-STYLE %pts - matches F1_ORB + F2_EMA5 exactly
    """
    
    if not candle_data or len(candle_data) < 9:
        if VERBOSE_LOGS:
            print(f"🔴 5EMA/9EMA {token}: Insufficient data ({len(candle_data)})")
        return {'score': 0.00, 'ema5': 0.00, 'ema9': 0.00}
    
    # ✅ TA-Lib EMA5 + EMA9 (keep existing logic)
    closes = np.array([
        safe_float(candle['intc'])
        for candle in candle_data
        if candle.get('stat') == 'Ok'
    ], dtype=float)
    
    if len(closes) < 9:
        if VERBOSE_LOGS:
            print(f"🔴 5EMA/9EMA {token}: Valid candles={len(closes)}")
        return {'score': 0.00, 'ema5': 0.00, 'ema9': 0.00}
    
    # 🔥 Calculate both EMAs
    try:
        talib.set_compatibility(1)
        ema5_values = talib.EMA(closes, timeperiod=5)
        ema9_values = talib.EMA(closes, timeperiod=9)
    finally:
        talib.set_compatibility(0)
    
    latest_ema5 = round(ema5_values[-1], 2)
    latest_ema9 = round(ema9_values[-1], 2)
    
    if latest_ema5 == 0:
        return {'score': 0.00, 'ema5': latest_ema5, 'ema9': latest_ema9}
    
    # 🎯 ORB-STYLE SIMPLE MATH (NO complex ratio/cap)
    dist_raw = latest_ema5 - latest_ema9
    dist_pct = safe_float(dist_raw / latest_ema5)
    f3_score = round(dist_pct * 100, 2)  # Raw %pts like F1/F2
    
    if VERBOSE_LOGS:
        dist_str = f"{abs(dist_pct*100):.2f}%"
        print(f"📊 F3_EMA5/9EMA {token}: EMA5=₹{latest_ema5:.2f} EMA9=₹{latest_ema9:.2f} "
              f"Dist={dist_str} F3={f3_score:>+5.2f}")
    
    # 🟢 Direction logic
    if latest_ema5 > latest_ema9:
        direction = "🟢 BULL"
    elif latest_ema5 < latest_ema9:
        direction = "🔴 BEAR"
    else:
        direction = "➖ FLAT"
        f3_score = 0.00
    
    if VERBOSE_LOGS and direction != "➖ FLAT":
        print(f"   {direction} F3={f3_score:>+5.2f}pts")
    
    return {
        'score': f3_score,
        'ema5': latest_ema5,
        'ema9': latest_ema9,
        'direction': direction
    }

"""
✅ FIXED - ORB-STYLE SIMPLIFIED (F1/F2/F3 CONSISTENT)
✅ (EMA5 - EMA9) / EMA5 × 100 = Raw %pts
✅ NO ratio, NO cap=0.10, NO 100x multiplier
✅ 2 decimal places everywhere
✅ Same return format: {'score': xx.xx, 'ema5': xx.xx, 'ema9': xx.xx}
✅ Drop-in replacement

BAJAJ-AUTO: EMA5=9637.42 EMA9=9587.52 → (9637-9587)/9637 = **+0.52pts** 🟢
COALINDIA:  EMA5=432.18 EMA9=442.20 → (432-442)/432 = **-2.32pts** 🔴

F1 + F2 + F3 = PERFECT TOTAL SIGNAL STRENGTH!
"""
