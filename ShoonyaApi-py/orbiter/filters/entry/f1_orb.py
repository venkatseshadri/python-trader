def orb_filter(data, weight=25, ema_histories=None):
    """
    Filter #1: ORB breakout → 25pts
    """
    ltp = float(data.get('lp', 0) or 0)
    return weight if ltp > 1450 else 0  # RELIANCE ORB level
