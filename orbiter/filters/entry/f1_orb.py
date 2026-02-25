#!/usr/bin/env python3
import json
import os
from datetime import datetime, timedelta
import math
from orbiter.utils.utils import safe_float

VERBOSE_LOGS = False

# 📂 Load Research Master for dynamic weighting
_base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_weights_path = os.path.join(_base, 'data', 'orb_weights_master.json')
ORB_RESEARCH_MASTER = {}
if os.path.exists(_weights_path):
    with open(_weights_path) as f:
        ORB_RESEARCH_MASTER = json.load(f)

def calculate_orb_range(ret, start_time_str='09:15', end_time_str='09:30', **kwargs):
    v_logs = kwargs.get('VERBOSE_LOGS', False)
    token = kwargs.get('token', 'UNKNOWN')
    if v_logs:
        print(f'🔍 API Response={len(ret) if ret else 0} candles')
    
    if not ret or len(ret) == 0:
        return None, None, None
    
    ok = [c for c in ret if c.get('stat') == 'Ok']

    def time_key(candle):
        raw = candle.get('time') or candle.get('tm') or candle.get('intt') or candle.get('t')
        if not raw: return None
        text = str(raw).strip()
        if ' ' in text: text = text.split(' ')[-1]
        parts = text.split(':')
        if len(parts) >= 2:
            try: return int(parts[0]) * 60 + int(parts[1])
            except: return None
        return None

    try:
        sh, sm = map(int, start_time_str.split(':'))
        eh, em = map(int, end_time_str.split(':'))
        orb_start = sh * 60 + sm
        orb_cutoff = eh * 60 + em
    except:
        orb_start, orb_cutoff = 9*60+15, 9*60+30
    
    orb_ok = []
    for c in ok:
        t = time_key(c)
        if t is not None and orb_start <= t <= orb_cutoff: orb_ok.append(c)

    if not orb_ok and ok: orb_ok = ok[:15]

    highs = [safe_float(c.get('inth') or c.get('h')) for c in orb_ok if (c.get('inth') or c.get('h')) is not None]
    lows = [safe_float(c.get('intl') or c.get('l')) for c in orb_ok if (c.get('intl') or c.get('l')) is not None]
    
    orb_open = None
    if orb_ok:
        first = orb_ok[0]
        orb_open = safe_float(first.get('into') or first.get('o') or first.get('intc') or first.get('c') or 0) or None
    
    if highs and lows:
        h_val, l_val = max(highs), min(lows)
        if v_logs: print(f'📊 ORB {token}: ₹{l_val:.2f} - ₹{h_val:.2f} (Open: ₹{orb_open or 0:.2f})')
        return h_val, l_val, orb_open
    return None, None, None

def orb_filter(data, ret, **kwargs):
    token = kwargs.get('token', 'UNKNOWN')
    v_logs = kwargs.get('VERBOSE_LOGS', False)
    ltp = safe_float(data.get('lp', 0) or 0)
    day_open = safe_float(data.get('o', 0) or data.get('pc', 0) or 0)
    
    if not token or ltp == 0: return {'score': 0.00, 'orb_high': 0.00, 'orb_low': 0.00, 'orb_size': 0.00}
    
    orb_high, orb_low, orb_open = calculate_orb_range(ret, **kwargs)
    if not orb_high or not orb_low: return {'score': 0.00, 'orb_high': 0.00, 'orb_low': 0.00, 'orb_size': 0.00}
    
    if day_open == 0 and orb_open: day_open = orb_open
    orbsize = orb_high - orb_low
    
    if ltp > orb_high:
        dist_pct = safe_float((ltp - orb_high) / ltp)
        distance_score = round(dist_pct * 100, 2)
    elif ltp < orb_low:
        dist_pct = safe_float((orb_low - ltp) / ltp)
        distance_score = round(-dist_pct * 100, 2)
    else:
        distance_score = 0.00
    
    mom_pct = (ltp - day_open) / ltp
    momentum_score = round(mom_pct * 100, 2)
    base_f1_score = distance_score + momentum_score
    
    symbol_name = token.split('|')[-1] if '|' in token else token
    research = ORB_RESEARCH_MASTER.get(symbol_name, {'reliability': 0.8, 'precision': 0.8, 'efficiency': 0.5})
    research_multiplier = research['reliability'] * research['precision'] * research['efficiency']
    f1_score = round(base_f1_score * research_multiplier, 2)
    
    if v_logs: print(f'📊 F1_REDEFINED {token}: Base={base_f1_score:>5.2f} x Mult={research_multiplier:.3f} -> Final F1={f1_score:>5.2f}')
    
    return {
        'score': f1_score,
        'orb_high': round(orb_high, 2),
        'orb_low': round(orb_low, 2),
        'orb_open': round(orb_open or 0, 2),
        'orb_size': round(orbsize, 2)
    }
