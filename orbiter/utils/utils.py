# orbiter/utils.py - Shoonya utilities
import datetime
import pytz

def safe_ltp(data, token=None):
    try:
        ltp_raw = data.get('lp', '0') if data else '0'
        ltp = float(ltp_raw) if ltp_raw else 0.0
        ltp_display = f"₹{ltp:.2f}"
        
        # PRIORITY: Company name → Formatted → Token → Fallback
        symbol = (data.get('t') or                    # 'RELIANCE' ⭐ BEST
                  data.get('symbol') or              # 'RELIANCE.NS'
                  data.get('name') or               # 'RELIANCE'
                  f"NSE|{token}" or                 # 'NSE|2885'
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

def get_today_orb_times():
    """Dynamic ORB: fixed 9:15-9:30 IST (temporarily pinned to 2026-02-09)."""
    # Fetch 1min candles for ORB between 9:15 and 9:30 IST.
    # TEMP: hardcode date for refactor verification; revert after test.
    ist = pytz.timezone('Asia/Kolkata')

    start_time = ist.localize(datetime.datetime(2026, 2, 9, 9, 15, 0))
    end_time = ist.localize(datetime.datetime(2026, 2, 9, 9, 30, 0))

    return start_time, end_time