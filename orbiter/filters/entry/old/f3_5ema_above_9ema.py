import talib
import numpy as np
from config.config import VERBOSE_LOGS, SCORE_CAP_EMA_CROSS_PCT


def ema5_above_9ema_filter(data, candle_data, token, weight=18):
    """F3: EMA5 > EMA9 with dynamic scoring based on EMA distance."""
    if not candle_data or len(candle_data) < 9:
        if VERBOSE_LOGS:
            print(f"🔴 5EMA/9EMA {token}: Insufficient data ({len(candle_data)})")
        return {'score': 0}

    closes = np.array([
        float(candle['intc'])
        for candle in candle_data
        if candle.get('stat') == 'Ok'
    ], dtype=float)

    if len(closes) < 9:
        if VERBOSE_LOGS:
            print(f"🔴 5EMA/9EMA {token}: Valid candles={len(closes)}")
        return {'score': 0}

    ema5 = talib.EMA(closes, timeperiod=5)
    ema9 = talib.EMA(closes, timeperiod=9)
    latest_ema5 = ema5[-1]
    latest_ema9 = ema9[-1]

    if latest_ema5 == 0:
        return {'score': 0, 'ema5': latest_ema5, 'ema9': latest_ema9}

    cap = SCORE_CAP_EMA_CROSS_PCT if SCORE_CAP_EMA_CROSS_PCT and SCORE_CAP_EMA_CROSS_PCT > 0 else 0.10
    dist = (latest_ema5 - latest_ema9) / latest_ema5
    score = 100.0 * max(-1.0, min(1.0, dist / cap))

    if VERBOSE_LOGS:
        print(
            f"📊 EMA5/EMA9 {token} EMA5={latest_ema5:.2f} EMA9={latest_ema9:.2f} score={score:.1f}"
        )

    return {'score': score, 'ema5': latest_ema5, 'ema9': latest_ema9}
