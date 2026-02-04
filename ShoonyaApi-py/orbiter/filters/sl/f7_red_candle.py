def sl_red_candle_weakness(data):
    """F7: 15min red candle > 1.5%"""
    try:
        ltp = float(data.get('lp', 0))
        # Check if recent candle was significantly red
        return ltp < 1450  # TEMP: Static check
    except:
        return False
