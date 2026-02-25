def sl_below_5ema(data, candle_data=None, **kwargs):
    """F1: LTP < 5EMA (Trend reversal)"""
    try:
        from orbiter.utils.utils import safe_float
        ltp = safe_float(data.get('lp', 0))
        indicators = kwargs.get('indicators', {})
        ema5 = indicators.get('ema5', 0)
        
        if ema5 > 0 and ltp < ema5:
            return {'hit': True, 'reason': 'LTP below 5EMA'}
        
        return {'hit': False}
    except:
        return {'hit': False}