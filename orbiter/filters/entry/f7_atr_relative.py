import numpy as np
import talib
from config.config import VERBOSE_LOGS
from utils.utils import safe_float

def atr_momentum_filter(data, candle_data, token, weight=10):
    """
    🎯 F7: ATR RELATIVE MOMENTUM (SOFT FILTER)
    Logic: Is the volatility (ATR) expanding or contracting?
    If ATR is less than its own 20-period average, momentum is dying.
    """
    if not candle_data or len(candle_data) < 30:
        return {'score': 0.00}

    highs = np.array([safe_float(c['inth']) for c in candle_data if c.get('stat')=='Ok'], dtype=float)
    lows = np.array([safe_float(c['intl']) for c in candle_data if c.get('stat')=='Ok'], dtype=float)
    closes = np.array([safe_float(c['intc']) for c in candle_data if c.get('stat')=='Ok'], dtype=float)

    if len(closes) < 25:
        return {'score': 0.00}

    # 1. Calculate ATR (14 period)
    atr = talib.ATR(highs, lows, closes, timeperiod=14)
    
    current_atr = atr[-1]
    # 2. Calculate ATR Baseline (20-period SMA of ATR)
    atr_baseline = np.mean(atr[-20:]) if len(atr) >= 20 else atr[-1]

    # 3. Calculate Relative Volatility (%)
    # If 1.0, ATR is exactly at baseline.
    # If < 1.0, Volatility is contracting.
    rel_vol = current_atr / atr_baseline if atr_baseline != 0 else 1.0

    score = 0.00
    # 4. Scoring Logic:
    # High Volatility (>1.10) = Bonus (+0.10)
    # Average Volatility (0.90 to 1.10) = Neutral (0.00)
    # Contraction (<0.90) = Penalty (-0.10)
    # Deep Contraction (<0.75) = Heavy Penalty (-0.20)
    
    if rel_vol > 1.10:   score = 0.10
    elif rel_vol > 0.90: score = 0.00
    elif rel_vol > 0.75: score = -0.10
    else:                score = -0.20

    if VERBOSE_LOGS:
        print(f"📊 F7_ATR {token}: ATR={current_atr:.2f} Base={atr_baseline:.2f} Rel={rel_vol:.2f} F7={score:>+5.2f}")

    return {
        'score': score,
        'rel_vol': round(rel_vol, 2),
        'atr': round(current_atr, 2)
    }
