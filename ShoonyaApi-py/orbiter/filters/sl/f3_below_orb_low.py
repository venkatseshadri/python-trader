def sl_below_orb_low(data):
    """F3: Price breaks ORB low"""
    try:
        ltp = float(data.get('lp', 0))
        orb_low = data.get('orb_low', ltp * 0.98)
        return ltp < orb_low
    except:
        return False
