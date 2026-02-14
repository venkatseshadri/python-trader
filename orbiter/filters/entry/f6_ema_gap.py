import numpy as np
import talib
from config.config import VERBOSE_LOGS
from utils.utils import safe_float

def ema_gap_expansion_filter(data, candle_data, token, weight=10):
    """
    🎯 F6: EMA GAP EXPANSION (ACCELERATION)
    Formula: (Gap[now] - Gap[prev]) / LTP * 100
    Gap = EMA5 - EMA9
    Positive: Gap is widening (Acceleration)
    Negative: Gap is narrowing (Deceleration/Convergence)
    """
    ltp = safe_float(data.get('lp', 0))
    if ltp == 0 or not candle_data or len(candle_data) < 15:
        return {'score': 0.00, 'gap_now': 0.00, 'gap_prev': 0.00}

    closes = np.array([safe_float(c['intc']) for c in candle_data if c.get('stat')=='Ok'], dtype=float)
    if len(closes) < 15:
        return {'score': 0.00}

    # Calculate EMAs
    try:
        talib.set_compatibility(1)
        ema5 = talib.EMA(closes, timeperiod=5)
        ema9 = talib.EMA(closes, timeperiod=9)
    finally:
        talib.set_compatibility(0)

    gap_now = ema5[-1] - ema9[-1]
    # Use 5-minute window for stable expansion (acceleration)
    gap_prev = (ema5[-6] - ema9[-6]) if len(ema5) >= 6 else (ema5[0] - ema9[0])

    # Expansion Logic: (Difference of Gaps over 5 mins)
    # We use raw difference to see direction and acceleration
    expansion_raw = (gap_now - gap_prev) / ltp
    f6_score = round(expansion_raw * 100, 2)

    if VERBOSE_LOGS:
        print(f"📊 F6_GAP {token}: Gap_Now={gap_now:.2f} Gap_Prev={gap_prev:.2f} F6={f6_score:>+5.2f}")

    return {
        'score': f6_score,
        'gap_now': round(gap_now, 2),
        'gap_prev': round(gap_prev, 2)
    }
