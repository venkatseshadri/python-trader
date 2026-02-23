import numpy as np
import talib
from config.config import VERBOSE_LOGS, SUPER_TREND_PERIOD, SUPER_TREND_MULTIPLIER
from utils.utils import safe_float

def calculate_st_values(highs, lows, closes, period, multiplier):
    """Internal helper to calculate SuperTrend array."""
    tr = np.zeros_like(closes)
    for i in range(1, len(closes)):
        tr[i] = max(highs[i] - lows[i], abs(highs[i] - closes[i-1]), abs(lows[i] - closes[i-1]))
    tr[0] = highs[0] - lows[0]
    
    # Standard TA-Lib EMA for ATR (Wilder's style)
    try:
        talib.set_compatibility(1) # Metastock compatibility
        atr = talib.EMA(tr, timeperiod=period * 2 - 1)
    finally:
        talib.set_compatibility(0)

    # Clean leading NaNs
    first_valid = np.where(~np.isnan(atr))[0]
    if len(first_valid) > 0:
        atr = np.nan_to_num(atr, nan=atr[first_valid[0]])
    else:
        atr = np.nan_to_num(atr, nan=0)

    hl2 = (highs + lows) / 2.0
    upper_band = hl2 + multiplier * atr
    lower_band = hl2 - multiplier * atr

    final_ub = np.copy(upper_band)
    final_lb = np.copy(lower_band)
    st = np.zeros_like(closes)

    for i in range(1, len(closes)):
        # Upper Band
        if upper_band[i] < final_ub[i-1] or closes[i-1] > final_ub[i-1]:
            final_ub[i] = upper_band[i]
        else:
            final_ub[i] = final_ub[i-1]
        
        # Lower Band
        if lower_band[i] > final_lb[i-1] or closes[i-1] < final_lb[i-1]:
            final_lb[i] = lower_band[i]
        else:
            final_lb[i] = final_lb[i-1]

    # Initialize trend
    st[0] = final_ub[0]
    for i in range(1, len(closes)):
        if st[i-1] == final_ub[i-1]:
            st[i] = final_ub[i] if closes[i] <= final_ub[i] else final_lb[i]
        else:
            st[i] = final_lb[i] if closes[i] >= final_lb[i] else final_ub[i]
            
    return st

def supertrend_filter(data, candle_data, **kwargs):
    """
    🎯 F4: BI-DIRECTIONAL STABILITY SCORE
    Anchor (15m): Trend Direction (Prevents Whipsaws)
    Momentum (5m): Slope Agreement (Quality Scoring)
    """
    token = kwargs.get('token')
    weight = kwargs.get('weight', 20)
    
    ltp = safe_float(data.get('lp', 0))
    if ltp == 0 or not candle_data or len(candle_data) < 30:
        return {'score': 0.00}

    # 1. Prepare Data
    highs = np.array([safe_float(c['inth']) for c in candle_data if c.get('stat')=='Ok'], dtype=float)
    lows = np.array([safe_float(c['intl']) for c in candle_data if c.get('stat')=='Ok'], dtype=float)
    closes = np.array([safe_float(c['intc']) for c in candle_data if c.get('stat')=='Ok'], dtype=float)

    if len(closes) < 20:
        return {'score': 0.00}

    # 2. Calculate SuperTrend Line (Full series)
    st_series = calculate_st_values(highs, lows, closes, SUPER_TREND_PERIOD, SUPER_TREND_MULTIPLIER)
    latest_st = st_series[-1]

    # 3. Timeframe Logic (using 1m history as proxy for high TFs)
    # 15m Anchor (Look back 15 candles)
    st_15m_ago = st_series[-15] if len(st_series) >= 15 else st_series[0]
    # 5m Momentum (Look back 5 candles)
    st_5m_ago = st_series[-5] if len(st_series) >= 5 else st_series[0]
    close_5m_ago = closes[-5] if len(closes) >= 5 else closes[0]

    # 4. Determine Direction (15m Anchor)
    # If LTP is on opposite side of ST than it was 15m ago, or direction mismatch, we check bias
    if ltp > latest_st:
        bias = "BULL"
    else:
        bias = "BEAR"

    # 5. Scoring Matrix based on Slopes (5m Window)
    # ST Slope: 1 (Up), 0 (Flat), -1 (Down)
    st_slope = 0
    if latest_st > st_5m_ago + 0.01: st_slope = 1
    elif latest_st < st_5m_ago - 0.01: st_slope = -1

    # Price Slope: 1 (Up), -1 (Down)
    price_slope = 1 if ltp >= close_5m_ago else -1

    score = 0.00

    if bias == "BULL":
        if st_slope == 1 and price_slope == 1:   score = 0.20 # Aggressive
        elif st_slope == 0 and price_slope == 1: score = 0.15 # Healthy Breakout
        elif st_slope == 1 and price_slope == -1:score = 0.10 # Pullback (Floor Rising)
        else:                                    score = 0.05 # Weakening
    else: # BEAR Bias
        if st_slope == -1 and price_slope == -1: score = -0.20 # Aggressive
        elif st_slope == 0 and price_slope == -1:score = -0.15 # Healthy Breakdown
        elif st_slope == -1 and price_slope == 1:score = -0.10 # Bear Rally (Ceiling Dropping)
        else:                                    score = -0.05 # Weakening Bear

    if VERBOSE_LOGS:
        slope_str = f"ST_Slp:{st_slope} P_Slp:{price_slope}"
        print(f"📊 F4_ST {token}: {bias} {slope_str} LTP={ltp:.2f} ST={latest_st:.2f} F4={score:>+5.2f}")

    return {
        'score': score,
        'supertrend': latest_st,
        'direction': "🟢 BULL" if bias == "BULL" else "🔴 BEAR"
    }
