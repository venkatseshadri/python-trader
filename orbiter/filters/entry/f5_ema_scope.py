import numpy as np
import talib
from config.config import VERBOSE_LOGS
from utils.utils import safe_float

def ema_scope_filter(data, candle_data, **kwargs):
    """
    🎯 F5: EMA SCOPE (VELOCITY)
    Formula: (EMA5[now] - EMA5[prev]) / LTP * 100
    Measures the 'tilt' or 'angle' of the EMA5.
    """
    token = kwargs.get('token')
    weight = kwargs.get('weight', 10)
    
    ltp = safe_float(data.get('lp', 0))
    if ltp == 0 or not candle_data or len(candle_data) < 10:
        return {'score': 0.00, 'ema5_now': 0.00, 'ema5_prev': 0.00}

    closes = np.array([safe_float(c['intc']) for c in candle_data if c.get('stat')=='Ok'], dtype=float)
    if len(closes) < 10:
        return {'score': 0.00}

    # Calculate EMA5
    try:
        talib.set_compatibility(1)
        ema5_series = talib.EMA(closes, timeperiod=5)
    finally:
        talib.set_compatibility(0)

    ema5_now = ema5_series[-1]
    # Use 5-minute window for stable scope (velocity)
    ema5_prev = ema5_series[-6] if len(ema5_series) >= 6 else ema5_series[0]

    # Calculate Scope (Raw %pts over 5 mins)
    scope_raw = (ema5_now - ema5_prev) / ltp
    f5_score = round(scope_raw * 100 * 5, 2)  # Scale by 5 to match ST weight

    # 🚦 THRESHOLD: Ignore noise/weak momentum (abs < 0.05 after scaling)
    if abs(f5_score) < 0.05:
        f5_score = 0.00
    
    # Cap at 0.20 to maintain balance
    f5_score = max(-0.20, min(0.20, f5_score))

    if VERBOSE_LOGS:
        print(f"📊 F5_SCOPE {token}: EMA5_Now={ema5_now:.2f} Prev={ema5_prev:.2f} F5={f5_score:>+5.2f}")

    return {
        'score': f5_score,
        'ema5_now': round(ema5_now, 2),
        'ema5_prev': round(ema5_prev, 2)
    }
