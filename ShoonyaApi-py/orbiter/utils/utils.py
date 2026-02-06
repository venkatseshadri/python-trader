# orbiter/utils.py - Shoonya utilities
import datetime
def safe_ltp(data, token=None):
    """
    Safely parse Shoonya LTP → (float, "₹1456.80")
    Handles: "1456.80", None, "", malformed strings
    """
    try:
        ltp_raw = data.get('lp', '0') if data else '0'
        ltp = float(ltp_raw) if ltp_raw else 0.0
        ltp_display = f"₹{ltp:.2f}"
        return ltp, ltp_display
    except (ValueError, TypeError, AttributeError):
        return 0.0, "₹0.00"

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
    """Dynamic ORB: Today's date + fixed 9:15-9:30"""
    # Fetch 1hr 1min data for EMA and for ORB between 9:15 and 9:30
    # now = int(time.time()) #UNCOMMENT for live production data
    # start = now - 3600     #UNCOMMENT for live production data
    today = datetime.datetime.today()
    
    # Today 9:15 AM
    orb_start = today.replace(
        hour=9, minute=15, second=0, microsecond=0
    )
    
    # Today 9:30 AM  
    orb_end = today.replace(
        hour=9, minute=30, second=0, microsecond=0
    )
    
    return orb_start, orb_end