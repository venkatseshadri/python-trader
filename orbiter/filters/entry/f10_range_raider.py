import talib
import numpy as np

def range_raider_filter(data, candles, **kwargs):
    """
    Sideways Mean Reversion Filter
    Returns +0.51 for Buy (Below Lower BB), -0.51 for Sell (Above Upper BB)
    """
    try:
        closes = np.array([float(c.get('intc', 0)) for c in candles if c.get('stat')=='Ok'], dtype=float)
        if len(closes) < 20:
            return 0
        
        # Use a slightly tighter BB for scalping
        upper, middle, lower = talib.BBANDS(closes, timeperiod=20, nbdevup=2, nbdevdn=2, matype=0)
        
        ltp = float(data.get('ltp', 0))
        if ltp <= 0: return 0
        
        # Signal Logic
        if ltp < lower[-1]:
            return 0.51 # High enough to trigger TRADE_SCORE=0.5
        elif ltp > upper[-1]:
            return -0.51
            
        return 0
    except Exception:
        return 0
