import numpy as np
import talib
from config.main_config import VERBOSE_LOGS, SCORE_CAP_ST_PCT, SUPER_TREND_PERIOD, SUPER_TREND_MULTIPLIER
from utils.utils import safe_float

def supertrend_filter(data, candle_data, token, weight=20, config=None):
    """F4: Supertrend distance scoring based on LTP vs ST line."""
    # return {'score': 0.0, 'supertrend': 0.0, 'ltp': 0.0} # REMOVED BAIL OUT
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

    atr = talib.ATR(highs, lows, closes, timeperiod=SUPER_TREND_PERIOD)
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
    st[0] = final_ub[0]
    for i in range(1, len(closes)):
        if st[i - 1] == final_ub[i - 1]:
            st[i] = final_ub[i] if closes[i] <= final_ub[i] else final_lb[i]
        else:
            st[i] = final_lb[i] if closes[i] >= final_lb[i] else final_ub[i]

    latest_st = safe_float(st[-1])
    if latest_st == 0:
        return {'score': 0}

    cap = SCORE_CAP_ST_PCT if SCORE_CAP_ST_PCT and SCORE_CAP_ST_PCT > 0 else 0.10
    dist = (ltp - latest_st) / ltp
    #score = 100.0 * max(-1.0, min(1.0, dist / cap))
    score = abs(dist / cap)

    if VERBOSE_LOGS:
        print(f"📊 ST {token} LTP={ltp:.2f} ST={latest_st:.2f} score={score:.1f}")

    return {'score': score, 'supertrend': latest_st}
