def sl_support_broken(data):
    """F10: Price < Previous Day Low (PDL)"""
    try:
        ltp = float(data.get('lp', 0))
        pdl = data.get('pdl', ltp * 0.97)  # Previous day low
        return ltp < pdl
    except:
        return False
