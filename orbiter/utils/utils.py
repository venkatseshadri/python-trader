# orbiter/utils.py - Shoonya utilities
import datetime
import pytz
import numpy as np
import math

def safe_ltp(data, token=None):
    try:
        ltp_raw = data.get('lp', '0') if data else '0'
        ltp = float(ltp_raw) if ltp_raw else 0.0
        ltp_display = f"₹{ltp:.2f}"
        
        fallback_token = token if token and "|" in str(token) else f"NSE|{token}"
        # PRIORITY: Company name → Formatted → Token → Fallback
        symbol = (data.get('t') or                    # 'RELIANCE' ⭐ BEST
                  data.get('symbol') or              # 'RELIANCE.NS'
                  data.get('name') or               # 'RELIANCE'
                  fallback_token or                 # 'NSE|2885' or 'NFO|...'
                  data.get('tk', 'UNKNOWN') or       # '2885'
                  'UNKNOWN')
        
        return ltp, ltp_display, symbol.strip().upper()
        
    except Exception:
        print(f"⚠️ safe_ltp FAILED: data={data}, token={token}")
        return 0.0, "₹0.00", "UNKNOWN"


def filter_status(weights):
    """Show which filters are active (-1 = DISABLED)"""
    status = []
    for i, w in enumerate(weights):
        status.append(f"F{i+1}:{w}" if w > 0 else f"F{i+1}:OFF")
    return status

def format_position(token, data):
    """Format position display string"""
    ltp, ltp_display = safe_ltp(data)
    tsym = data.get('ts', token)
    return f"{tsym} {ltp_display}"

def format_score(score):
    if score >= 25:   return f" 🟢 ENTRY {int(score)}"
    return f" 🔴 HOLD{int(score)}"

def get_today_orb_times(market_open, market_close, simulation: bool = False):
    """Dynamic ORB window based on segment hours."""
    ist = pytz.timezone('Asia/Kolkata')
    now_ist = datetime.datetime.now(tz=ist)

    trading_day = now_ist
    if simulation:
        trading_day = trading_day - datetime.timedelta(days=1)

    while trading_day.weekday() >= 5:
        trading_day = trading_day - datetime.timedelta(days=1)

    start_time = trading_day.replace(hour=market_open.hour, minute=market_open.minute, second=0, microsecond=0)
    market_close_dt = trading_day.replace(hour=market_close.hour, minute=market_close.minute, second=0, microsecond=0)
    
    if simulation:
        end_time = market_close_dt
    else:
        if now_ist < start_time:
            end_time = start_time
        elif now_ist > market_close_dt:
            end_time = market_close_dt
        else:
            end_time = now_ist

    return start_time, end_time

def safe_float(value, default=0.0):
    """🔒 BULLETPROOF float conversion (JSON Compliant)"""
    if value is None:
        return default
    try:
        if isinstance(value, str):
            cleaned = value.strip().replace(',', '')
            num = float(cleaned)
        else:
            num = float(value)
        
        # ✅ Check for JSON non-compliant floats
        if math.isnan(num) or math.isinf(num):
            return default
        return num
    except (ValueError, TypeError):
        return default

# REPLACE ALL float(candle['intc']) → safe_float(candle['intc'])

def safe_price_array(candle_data, min_len=5):
    """🔥 RETURNS np.float64 OR None - NO object dtype EVER"""
    prices = []
    for candle in candle_data or []:
        if isinstance(candle, dict) and candle.get('stat') == 'Ok':
            price = safe_float(candle.get('intc') or candle.get('c'))
            if price > 0:
                prices.append(price)
    
    if len(prices) < min_len:
        return None
    
    # 🔥 FORCE np.float64 - TALIB SAFE
    arr = np.array(prices)
    if arr.dtype != np.float64:
        arr = arr.astype(np.float64)
    return arr