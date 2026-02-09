# f1_orb.py - PURE MODULE FUNCTIONS (NO CLASS)
from datetime import datetime, timedelta

def calculate_orb_range(ret, token,):
    """FIXED: Precise 9:15-9:30 ORB (1min candles)"""

    print(f"🔍 API Response={len(ret) if ret else 0} candles")
    
    if ret and len(ret) > 0:
        highs = [float(c['inth']) for c in ret if c.get('stat') == 'Ok']
        lows = [float(c['intl']) for c in ret if c.get('stat') == 'Ok']
        if highs and lows:
            print(f"📊 ORB {token}: ₹{min(lows):.2f} - ₹{max(highs):.2f}")
            return max(highs), min(lows)
    return None, None


def orb_filter(data, ret, weight=25, token='', buffer_pct=0.2):
    """Main ORB filter - uses calculate_orb_range helper"""
    # token = data.get('token', '')
    ltp = float(data.get('lp', 0) or 0)
    
    if not token or ltp == 0:
        return {'score': 0, 'orb_high': 0, 'orb_low': 0}   # ⭐ CHANGED
    
    buf = buffer_pct / 100
    upper, lower = calculate_orb_range(ret, token)
    
    if not upper or not lower:
        return {'score': 0, 'orb_high': 0, 'orb_low': 0}  # ⭐ CHANGED
    
    if ltp > upper * (1 + buf):
        print(f"🟢 ORB BULL {token}: ₹{ltp:.2f} > ₹{upper:.2f}")
        return {'score': weight, 'orb_high': upper, 'orb_low': lower}  # ⭐ CHANGED
    elif ltp < lower * (1 - buf):
        print(f"🔴 ORB BEAR {token}: ₹{ltp:.2f} < ₹{lower:.2f}")
        return {'score': weight, 'orb_high': upper, 'orb_low': lower}  # ⭐ CHANGED
    
    return {'score': 0, 'orb_high': upper, 'orb_low': lower}  # ⭐ CHANGED

def get_today_orb_times():
    """Dynamic ORB: Today's date + fixed 9:15-9:30"""
    today = datetime.today()
    
    # Today 9:15 AM
    orb_start = today.replace(
        hour=9, minute=15, second=0, microsecond=0
    )
    
    # Today 9:30 AM  
    orb_end = today.replace(
        hour=9, minute=30, second=0, microsecond=0
    )
    
    return orb_start, orb_end