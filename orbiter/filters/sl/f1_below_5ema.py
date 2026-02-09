def sl_below_5ema(data):
    """F1: LTP < 5EMA (Trend reversal)"""
    try:
        ltp = float(data.get('lp', 0))
        # EMA calculation will be added later
        return ltp < 1440  # TEMP: Static threshold
    except:
        return False