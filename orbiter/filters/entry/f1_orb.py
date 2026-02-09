# f1_orb.py - PURE MODULE FUNCTIONS (NO CLASS)
from datetime import datetime, timedelta

def calculate_orb_range(ret, token,):
    """FIXED: Precise 9:15-9:30 ORB (1min candles)"""

    print(f"🔍 API Response={len(ret) if ret else 0} candles")
    
    if ret and len(ret) > 0:
        ok = [c for c in ret if c.get('stat') == 'Ok']
        highs = [float(c['inth']) for c in ok if c.get('inth') is not None]
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
            orb_open = float(first.get('into') or first.get('intc') or 0) or None

        if highs and lows:
            print(f"📊 ORB {token}: ₹{min(lows):.2f} - ₹{max(highs):.2f}")
            return max(highs), min(lows), orb_open
    return None, None, None


def orb_filter(data, ret, weight=25, token='', buffer_pct=0.2):
    """Main ORB filter - uses calculate_orb_range helper"""
    # token = data.get('token', '')
    ltp = float(data.get('lp', 0) or 0)
    
    if not token or ltp == 0:
        return {'score': 0, 'orb_high': 0, 'orb_low': 0, 'orb_open': 0}
    
    buf = buffer_pct / 100
    upper, lower, orb_open = calculate_orb_range(ret, token)
    
    if not upper or not lower:
        return {'score': 0, 'orb_high': 0, 'orb_low': 0, 'orb_open': 0}
    
    if ltp > upper * (1 + buf):
        print(f"🟢 ORB BULL {token}: ₹{ltp:.2f} > ₹{upper:.2f}")
        return {
            'score': weight,
            'orb_high': upper,
            'orb_low': lower,
            'orb_open': orb_open
        }
    elif ltp < lower * (1 - buf):
        print(f"🔴 ORB BEAR {token}: ₹{ltp:.2f} < ₹{lower:.2f}")
        return {
            'score': -weight,
            'orb_high': upper,
            'orb_low': lower,
            'orb_open': orb_open
        }

    return {'score': 0, 'orb_high': upper, 'orb_low': lower, 'orb_open': orb_open}

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