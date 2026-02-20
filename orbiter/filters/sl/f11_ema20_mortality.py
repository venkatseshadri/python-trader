import pandas as pd
import talib
import numpy as np
from utils.utils import safe_float

def resample_to_15min(minute_candles):
    """
    Convert list of 1-min candle dicts to 15-min DataFrame.
    """
    if not minute_candles:
        return pd.DataFrame()

    df = pd.DataFrame(minute_candles)
    
    # Map Shoonya keys
    # Keys usually: ssboe, into, inth, intl, intc, v, time
    if 'time' in df.columns:
        df['time'] = pd.to_datetime(df['time'], format='mixed')
    elif 'ssboe' in df.columns:
        # ssboe is seconds since epoch
        df['time'] = pd.to_datetime(df['ssboe'], unit='s')
    else:
        return pd.DataFrame()
        
    for c in ['into', 'inth', 'intl', 'intc', 'v']:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors='coerce')

    df = df.set_index('time')
    
    # Resample 15T
    ohlc_dict = {
        'into': 'first',
        'inth': 'max',
        'intl': 'min',
        'intc': 'last',
        'v': 'sum'
    }
    
    df_15 = df.resample('15min').agg(ohlc_dict).dropna()
    
    return df_15

def trend_mortality_sl(position, ltp, data):
    """
    🎯 SL: TREND MORTALITY (15-min EMA20)
    Law: If 15m candle closes below EMA20, the trend is dead (61% probability).
    """
    raw_candles = data.get('candles', [])
    if not raw_candles or len(raw_candles) < 60: 
        return {'hit': False}

    # 1. Resample to 15-min
    df_15 = resample_to_15min(raw_candles)
    
    if len(df_15) < 20: 
        return {'hit': False}

    # 2. Calculate EMA 20 using TALIB
    closes = df_15['intc'].values.astype(float)
    try:
        talib.set_compatibility(1) # Metastock compatibility
        ema_series = talib.EMA(closes, timeperiod=20)
    finally:
        talib.set_compatibility(0)
        
    df_15['EMA20'] = ema_series
    
    # 3. Check Last COMPLETED Candle
    if len(df_15) < 2:
        return {'hit': False}
        
    last_completed = df_15.iloc[-2]
    
    close_price = last_completed['intc']
    ema_val = last_completed['EMA20']
    
    if np.isnan(ema_val):
        return {'hit': False}

    strategy = position.get('strategy', 'PUT_CREDIT_SPREAD')

    # 4. Logic: Trend Death
    if 'PUT' in strategy or 'LONG' in strategy: # Bullish
        if close_price < ema_val:
            return {
                'hit': True, 
                'reason': f"💀 Trend Mortality: 15m Close ({close_price}) < EMA20 ({ema_val:.2f})",
                'pct': 0.0
            }
            
    elif 'CALL' in strategy or 'SHORT' in strategy: # Bearish
        if close_price > ema_val:
            return {
                'hit': True, 
                'reason': f"💀 Trend Mortality: 15m Close ({close_price}) > EMA20 ({ema_val:.2f})",
                'pct': 0.0
            }

    return {'hit': False}
