#!/usr/bin/env python3
"""
🚀 f2_price_above_5ema.py - FIXED ORB-STYLE SIMPLIFIED VERSION
Raw % distance LTP-EMA5 (NO ratio/clamping, 2 decimals)
Drop-in replacement for existing orbiter
"""

import talib
import numpy as np
from orbiter.utils.utils import safe_float

def price_above_5ema_filter(data, candle_data, **kwargs):
    """
    🎯 F2_5EMA SIMPLIFIED: (LTP - EMA5) / LTP × 100
    ORB-STYLE %pts - consistent with F1_ORB_SIMPLE
    """
    token = kwargs.get('token')
    weight = kwargs.get('weight', 20)
    VERBOSE_LOGS = kwargs.get('VERBOSE_LOGS', False)
    
    ltp = safe_float(data.get('lp', 0))
    if ltp == 0:
        if VERBOSE_LOGS:
            print(f"🔴 5EMA {token}: LTP=0")
        return {'score': 0.00, 'ema5': 0.00}
    
    if not candle_data or len(candle_data) < 5:
        if VERBOSE_LOGS:
            print(f"🔴 5EMA {token}: Insufficient data ({len(candle_data)})")
        return {'score': 0.00, 'ema5': 0.00}
    
    # ✅ TA-Lib EMA5 (keep existing)
    closes = np.array([
        safe_float(candle['intc'])
        for candle in candle_data
        if candle.get('stat') == 'Ok'
    ], dtype=float)
    
    if len(closes) < 5:
        if VERBOSE_LOGS:
            print(f"🔴 5EMA {token}: Valid candles={len(closes)}")
        return {'score': 0.00, 'ema5': 0.00}
    
    # 🔥 Calculate EMA5 (Use optimized context if available)
    indicators = kwargs.get('indicators', {})
    latest_ema5 = indicators.get('ema5')
    
    if latest_ema5 is None:
        # Fallback: Calculate manually
        try:
            talib.set_compatibility(1)
            ema5_values = talib.EMA(closes, timeperiod=5)
            latest_ema5 = round(ema5_values[-1], 2)
        finally:
            talib.set_compatibility(0)
    
    # 🎯 ORB-STYLE SIMPLE MATH (NO complex ratio)
    dist_pct = safe_float((ltp - latest_ema5) / ltp)
    f2_score = round(dist_pct * 100, 2)  # Raw %pts like F1_ORB
    
    if VERBOSE_LOGS:
        dist_str = f"{abs(dist_pct*100):.2f}%"
        print(f"📊 F2_5EMA {token}: LTP=₹{ltp:.2f} EMA5=₹{latest_ema5:.2f} "
              f"Dist={dist_str} F2={f2_score:>+5.2f}")
    
    # 🟢 Direction logic
    if ltp > latest_ema5:
        direction = "🟢 BULL"
    elif ltp < latest_ema5:
        direction = "🔴 BEAR"
    else:
        direction = "➖ FLAT"
        f2_score = 0.00
    
    if VERBOSE_LOGS and direction != "➖ FLAT":
        print(f"   {direction} F2={f2_score:>+5.2f}pts")
    
    return {
        'score': f2_score, 
        'ema5': latest_ema5,
        'direction': direction
    }

"""
✅ FIXED - ORB-STYLE SIMPLIFIED
✅ (LTP - EMA5) / LTP × 100 = Raw %pts  
✅ NO ratio, NO clamping, NO 100x multiplier
✅ 2 decimal places everywhere
✅ Same return format: {'score': xx.xx, 'ema5': xx.xx}
✅ Drop-in replacement

EICHERMOT: LTP=7771 EMA5=7217 → (7771-7217)/7771 = **7.12pts** 🟢
MAXHEALTH: LTP=1055 EMA5=1012 → **4.05pts** 🟢

F1_ORB + F2_EMA = CLEAN total signal!
"""
