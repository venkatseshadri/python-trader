import numpy as np
import talib
from config.config import VERBOSE_LOGS, SCORE_CAP_ST_PCT, SUPER_TREND_PERIOD, SUPER_TREND_MULTIPLIER
from utils.utils import safe_float

def supertrend_filter(data, candle_data, token, weight=20):
    """F4: Supertrend distance scoring based on LTP vs ST line."""
    ltp = safe_float(data.get('lp', 0) or 0)
    if ltp == 0:
        return {'score': 0}

    if not candle_data or len(candle_data) < SUPER_TREND_PERIOD + 2:
        if VERBOSE_LOGS:
            print(f"🔴 ST {token}: Insufficient data ({len(candle_data)})")
        return {'score': 0}

    highs = np.array([
        safe_float(candle['inth'])
        for candle in candle_data
        if candle.get('stat') == 'Ok'
    ], dtype=float)
    lows = np.array([
        safe_float(candle['intl'])
        for candle in candle_data
        if candle.get('stat') == 'Ok'
    ], dtype=float)
    closes = np.array([
        safe_float(candle['intc'])
        for candle in candle_data
        if candle.get('stat') == 'Ok'
    ], dtype=float)

    if len(closes) < SUPER_TREND_PERIOD + 2:
        if VERBOSE_LOGS:
            print(f"🔴 ST {token}: Valid candles={len(closes)}")
        return {'score': 0}

    tr = np.zeros_like(closes)
    for i in range(1, len(closes)):
        tr[i] = max(highs[i] - lows[i], abs(highs[i] - closes[i-1]), abs(lows[i] - closes[i-1]))
    tr[0] = highs[0] - lows[0]
    
    # Use simple average for the first period, then EMA for ATR (Wilder's style)
    atr = talib.EMA(tr, timeperiod=SUPER_TREND_PERIOD * 2 - 1)
    
    # ✅ Force remove all nans from ATR for stability
    if np.isnan(atr[0]):
        # Fill leading nans with the first valid ATR or mean
        first_valid_idx = np.where(~np.isnan(atr))[0]
        if len(first_valid_idx) > 0:
            fill_val = atr[first_valid_idx[0]]
            atr = np.nan_to_num(atr, nan=fill_val)
        else:
            atr = np.nan_to_num(atr, nan=np.mean(tr))

    hl2 = (highs + lows) / 2.0
    basic_ub = hl2 + SUPER_TREND_MULTIPLIER * atr
    basic_lb = hl2 - SUPER_TREND_MULTIPLIER * atr

    final_ub = np.copy(basic_ub)
    final_lb = np.copy(basic_lb)

    for i in range(1, len(closes)):
        if basic_ub[i] < final_ub[i - 1] or closes[i - 1] > final_ub[i - 1]:
            final_ub[i] = basic_ub[i]
        else:
            final_ub[i] = final_ub[i - 1]

        if basic_lb[i] > final_lb[i - 1] or closes[i - 1] < final_lb[i - 1]:
            final_lb[i] = basic_lb[i]
        else:
            final_lb[i] = final_lb[i - 1]

    st = np.zeros_like(closes)
    # Find first non-nan index
    non_nan_indices = np.where(~np.isnan(final_ub))[0]
    if len(non_nan_indices) == 0:
        return {'score': 0}
    
    start_idx = non_nan_indices[0]
    st[start_idx] = final_ub[start_idx]
    for i in range(start_idx + 1, len(closes)):
        if st[i - 1] == final_ub[i - 1]:
            st[i] = final_ub[i] if closes[i] <= final_ub[i] else final_lb[i]
        else:
            st[i] = final_lb[i] if closes[i] >= final_lb[i] else final_ub[i]
    
    latest_st = safe_float(st[-1])
    if latest_st == 0 or np.isnan(latest_st):
        return {'score': 0}

    cap = SCORE_CAP_ST_PCT if SCORE_CAP_ST_PCT and SCORE_CAP_ST_PCT > 0 else 0.10
    dist = (ltp - latest_st) / ltp
    #score = 100.0 * max(-1.0, min(1.0, dist / cap))
    score = abs(dist / cap)

    if VERBOSE_LOGS:
        print(f"📊 ST {token} LTP={ltp:.2f} ST={latest_st:.2f} score={score:.1f}")

    return {'score': score, 'supertrend': latest_st}
