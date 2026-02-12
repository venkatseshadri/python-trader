# f1_orb.py - PURE MODULE FUNCTIONS (NO CLASS)
from datetime import datetime, timedelta
import math
from config.config import (
    VERBOSE_LOGS,
    SCORE_W_ORB_SIZE,
    SCORE_W_ORB_HIGH,
    SCORE_W_ORB_LOW,
    SCORE_SCALE_ORB_SIZE_PCT,
    SCORE_SCALE_ORB_BREAK_PCT,
)
from utils.utils import safe_float, safe_price_array

def calculate_orb_range(ret, token,):
    """FIXED: Precise 9:15-9:30 ORB (1min candles)"""

    if VERBOSE_LOGS:
        print(f"🔍 API Response={len(ret) if ret else 0} candles")
    
    if ret and len(ret) > 0:
        ok = [c for c in ret if c.get('stat') == 'Ok']
        highs = [safe_float(c['inth']) for c in ok if c.get('inth') is not None]
        lows = [float(c['intl']) for c in ok if c.get('intl') is not None]
        orb_open = None
        if ok:
            def _time_key(candle):
                raw = candle.get('time') or candle.get('tm') or candle.get('intt') or candle.get('t')
                if not raw:
                    return None
                text = str(raw)
                for sep in (" ", ":"):
                    text = text.replace(sep, ":")
                parts = text.split(":")
                if len(parts) >= 2:
                    try:
                        hour = int(parts[0])
                        minute = int(parts[1])
                        return hour * 60 + minute
                    except ValueError:
                        return None
                return None

            keyed = [(c, _time_key(c)) for c in ok]
            with_time = [pair for pair in keyed if pair[1] is not None]
            first = min(with_time, key=lambda x: x[1])[0] if with_time else ok[0]
            orb_open = safe_float(first.get('into') or first.get('intc') or 0) or None

        if highs and lows:
            if VERBOSE_LOGS:
                print(f"📊 ORB {token}: ₹{min(lows):.2f} - ₹{max(highs):.2f}")
            return max(highs), min(lows), orb_open
    return None, None, None


def orb_filter(data, ret, weight=25, token='', buffer_pct=0.2):
    """Main ORB filter - uses calculate_orb_range helper"""
    # token = data.get('token', '')
    ltp = safe_float(data.get('lp', 0) or 0)
    
    if not token or ltp == 0:
        return {'score': 0, 'orb_high': 0, 'orb_low': 0, 'orb_open': 0}
    
    buf = buffer_pct / 100
    upper, lower, orb_open = calculate_orb_range(ret, token)
    
    if not upper or not lower:
        return {'score': 0, 'orb_high': 0, 'orb_low': 0, 'orb_open': 0}
    
    size_scale = SCORE_SCALE_ORB_SIZE_PCT if SCORE_SCALE_ORB_SIZE_PCT and SCORE_SCALE_ORB_SIZE_PCT > 0 else 0.05
    break_scale = SCORE_SCALE_ORB_BREAK_PCT if SCORE_SCALE_ORB_BREAK_PCT and SCORE_SCALE_ORB_BREAK_PCT > 0 else 0.10

    orb_size = (upper - lower) / ltp
    size_score = SCORE_W_ORB_SIZE * math.tanh(orb_size / size_scale)

    if ltp > upper * (1 + buf):
        dist = (ltp - upper) / ltp
        high_score = SCORE_W_ORB_HIGH * math.tanh(dist / break_scale)
        score = size_score + high_score
        if VERBOSE_LOGS:
            print(
                f"🟢 ORB BULL {token}: ₹{ltp:.2f} > ₹{upper:.2f} "
                f"size={size_score:.1f} high={high_score:.1f} total={score:.1f}"
            )
        return {
            'score': score,
            'orb_high': upper,
            'orb_low': lower,
            'orb_open': orb_open,
        }

    if ltp < lower * (1 - buf):
        dist = (ltp - lower) / ltp
        low_score = SCORE_W_ORB_LOW * math.tanh(dist / break_scale)
        score = -size_score + low_score
        if VERBOSE_LOGS:
            print(
                f"🔴 ORB BEAR {token}: ₹{ltp:.2f} < ₹{lower:.2f} "
                f"size={size_score:.1f} low={low_score:.1f} total={score:.1f}"
            )
        return {
            'score': score,
            'orb_high': upper,
            'orb_low': lower,
            'orb_open': orb_open,
            'orb_size': upper - lower
        }

    return {'score': 0, 'orb_high': upper, 'orb_low': lower, 'orb_open': orb_open, 'orb_size': upper - lower}

def get_today_orb_times():
    """Dynamic ORB: Today's date + fixed 9:15-9:30"""
    today = datetime.today()
    
    # Today 9:15 AM
    start_time = today.replace(
        hour=9, minute=15, second=0, microsecond=0
    )
    
    # Today 9:30 AM  
    end_time = today.replace(
        hour=9, minute=30, second=0, microsecond=0
    )
    
    return start_time, end_time