#!/usr/bin/env python3
"""
🚀 f1_orb_simple.py - SIMPLIFIED F1_ORB (2/3 Momentum + 1/3 Distance)
2 DECIMAL PLACES - Production ready drop-in replacement
"""

from datetime import datetime, timedelta
import math
from config.config import VERBOSE_LOGS
from utils.utils import safe_float

def calculate_orb_range(ret, token):
    """KEEP EXISTING ORB RANGE CALC (9:15-9:30 1min candles)"""
    if VERBOSE_LOGS:
        print(f"🔍 API Response={len(ret) if ret else 0} candles")
    
    if not ret or len(ret) == 0:
        return None, None, None
    
    ok = [c for c in ret if c.get('stat') == 'Ok']
    highs = [safe_float(c.get('inth')) for c in ok if c.get('inth') is not None]
    lows = [safe_float(c.get('intl')) for c in ok if c.get('intl') is not None]
    
    orb_open = None
    if ok:
        def time_key(candle):
            raw = candle.get('time') or candle.get('tm') or candle.get('intt') or candle.get('t')
            if not raw: return None
            text = str(raw).strip()
            if " " in text:
                text = text.split(" ")[-1]
            parts = text.split(":")
            if len(parts) >= 2:
                try:
                    hour = int(parts[0])
                    minute = int(parts[1])
                    return hour * 60 + minute
                except ValueError:
                    return None
            return None
        
        keyed = [(c, time_key(c)) for c in ok]
        with_time = [pair for pair in keyed if pair[1] is not None]
        first = min(with_time, key=lambda x: x[1]) if with_time else ok[0]
        orb_open = safe_float(first[0].get('into') or first[0].get('o') or 0) or None
    
    if highs and lows:
        if VERBOSE_LOGS:
            print(f"📊 ORB {token}: ₹{min(lows):.2f} - ₹{max(highs):.2f}")
        return max(highs), min(lows), orb_open
    return None, None, None

def orb_filter(data, ret, weight=25, token=None, buffer_pct=0.2):
    """
    🎯 SIMPLIFIED F1_ORB: 2/3 MOMENTUM + 1/3 DISTANCE (2 DECIMAL PLACES)
    """
    ltp = safe_float(data.get('lp', 0) or 0)
    day_open = safe_float(data.get('o', 0) or data.get('pc', 0) or 0)
    
    if not token or ltp == 0:
        return {'score': 0.00, 'orb_high': 0.00, 'orb_low': 0.00, 'orb_size': 0.00}
    
    # GET ORB RANGE
    orb_high, orb_low, orb_open = calculate_orb_range(ret, token)
    if not orb_high or not orb_low:
        return {'score': 0.00, 'orb_high': 0.00, 'orb_low': 0.00, 'orb_size': 0.00}
    
    # ✅ FIX: Use orb_open (9:15 candle) if live day_open is missing/zero
    if day_open == 0 and orb_open:
        day_open = orb_open

    orbsize = orb_high - orb_low
    
    # 1️⃣ DISTANCE SCORE (1/3 weight = 33.33pts max)
    if ltp > orb_high:
        dist_pct = safe_float((ltp - orb_high) / ltp)
        distance_score = round(dist_pct * 33.33, 2)  # 2 decimals
        direction = "🟢 ORB BULL"
    elif ltp < orb_low:
        dist_pct = safe_float((orb_low - ltp) / ltp)
        distance_score = round(-dist_pct * 33.33, 2)  # 2 decimals
        direction = "🔴 ORB BEAR"
    else:
        distance_score = 0.00
        direction = "➖ INSIDE"
    
    # 2️⃣ MOMENTUM SCORE (2/3 weight = 66.67pts max)
    mom_pct = abs(day_open - ltp) / ltp
    momentum_score = round(mom_pct * 66.67, 2)  # 2 decimals
    
    # 3️⃣ TOTAL F1 (2 decimals)
    f1_score = round(distance_score + momentum_score, 2)
    
    if VERBOSE_LOGS:
        dist_str = f"{abs(dist_pct*100):.2f}%" if 'dist_pct' in locals() and dist_pct != 0 else "0.00%"
        mom_str = f"{mom_pct*100:.2f}%"
        print(f"📊 F1_SIMPLE {token}: D={dist_str:>5} M={mom_str:>5} F1={f1_score:>5.2f} {direction}")
    
    #return f1_score, round(orb_high, 2), round(orb_low, 2), round(orb_open or 0, 2), round(orbsize, 2)
    return {
        'score': f1_score,
        'orb_high': round(orb_high, 2),
        'orb_low': round(orb_low, 2),
        'orb_size': round(orbsize, 2)
    }

def get_today_orb_times():
    """Existing ORB time logic"""
    today = datetime.today()
    start_time = today.replace(hour=9, minute=15, second=0, microsecond=0)
    end_time = today.replace(hour=9, minute=30, second=0, microsecond=0)
    return start_time, end_time
