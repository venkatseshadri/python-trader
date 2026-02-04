# orbiter/utils.py - Shoonya utilities
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
