#def price_above_5ema_filter(data, weight=20, ema_histories=None):
    # """
    # Filter #2: LTP > 5EMA → 20pts
    # """
    # ltp = float(data.get('lp', 0) or 0)
    
    # if ema_histories is None:
    #     ema_histories = {}
    
    # token = data.get('tk', 'unknown')
    
    # # 🔥 BULLETPROOF structure
    # if token not in ema_histories or not isinstance(ema_histories[token], dict):
    #     ema_histories[token] = {'ema5': {'prices': [], 'ema': 0}}
    
    # try:
    #     ema5_data = ema_histories[token]['ema5']
    #     ema5_data['prices'].append(ltp)
    #     if len(ema5_data['prices']) > 5:
    #         ema5_data['prices'].pop(0)
    #     ema5_data['ema'] = sum(ema5_data['prices']) / len(ema5_data['prices'])
        
    #     return weight if ltp > ema5_data['ema'] > 0 else 0
    # except:
    #     return 0

import talib
import numpy as np
import pandas as pd
import time
from datetime import datetime

def price_above_5ema_filter(data, candle_data, token, weight=20):
    """F2: TA-Lib EMA5 → 20pts (ULTRA FAST)"""
    ltp = float(data.get('lp', 0))
    if ltp == 0: 
        print(f"🔴 5EMA {token}: LTP=0")
        return 0
        
    if not candle_data or len(candle_data) < 5:
        print(f"🔴 5EMA {token}: Insufficient data ({len(candle_data)})")
        return 0
    
    # ✅ FIXED LIST COMPREHENSION
    closes = np.array([
        float(candle['intc']) 
        for candle in candle_data 
        if candle.get('stat') == 'Ok'
    ], dtype=float)
    
    if len(closes) < 5:
        print(f"🔴 5EMA {token}: Valid candles={len(closes)}")
        return 0
    
    # 🔥 TA-Lib MAGIC
    ema5 = talib.EMA(closes, timeperiod=5)
    latest_ema = ema5[-1]
    
    print(f"📊 TA-Lib 5EMA {token} LTP={ltp:.2f} EMA5={latest_ema:.2f}")
    
    if ltp > latest_ema:
        print(f"🟢 5EMA BULL {token}: {ltp:.2f} > {latest_ema:.2f} → +{weight}pts")
        return weight
    else:
        print(f"🔴 5EMA FAIL {token}: {ltp:.2f} <= {latest_ema:.2f}")
        return 0