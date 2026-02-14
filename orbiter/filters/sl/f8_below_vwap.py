def sl_below_vwap(data):
    """F8: LTP < VWAP (institutional selling)"""
    try:
        ltp = float(data.get('lp', 0))
        vwap = data.get('vwap', ltp * 1.01)
        return ltp < vwap * 0.998
    except:
        return False
