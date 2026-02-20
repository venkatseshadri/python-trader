import pandas as pd
import pandas_ta as ta
from utils.utils import safe_float

def resample_to_15min(minute_candles):
    """
    Convert list of 1-min candle dicts to 15-min DataFrame.
    """
    if not minute_candles:
        return pd.DataFrame()

    df = pd.DataFrame(minute_candles)
    
    # Ensure numeric columns
    cols = ['into', 'inth', 'intl', 'intc', 'v']
    # Map API keys if needed (ss keys usually: into, inth, intl, intc, v)
    # Check first row keys
    first = minute_candles[0]
    if 'time' in first: # Shoonya format
        df['time'] = pd.to_datetime(df['time'], format='%d-%m-%Y %H:%M:%S')
    elif 'time' not in first and 'ssboe' in first:
        # Fallback or different format handling
        return pd.DataFrame()
        
    for c in ['into', 'inth', 'intl', 'intc', 'v']:
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
    
    # Identify closed candles only? 
    # For now, resample everything. We will drop the last row if it's incomplete in the logic.
    df_15 = df.resample('15min').agg(ohlc_dict).dropna()
    
    return df_15

def trend_mortality_sl(position, ltp, data):
    """
    🎯 SL: TREND MORTALITY (15-min EMA20)
    Law: If 15m candle closes below EMA20, the trend is dead (61% probability).
    """
    raw_candles = data.get('candles', [])
    if not raw_candles or len(raw_candles) < 60: # Need enough for 15m resampling
        return {'hit': False}

    # 1. Resample to 15-min
    df_15 = resample_to_15min(raw_candles)
    
    if len(df_15) < 20: # Need at least 20 bars for EMA20
        return {'hit': False}

    # 2. Calculate EMA 20
    df_15['EMA20'] = ta.ema(df_15['intc'], length=20)
    
    # 3. Check Last COMPLETED Candle
    # The last row in df_15 might be the current forming candle.
    # We want the 'Close' of the *previous* fully formed 15m candle.
    
    # Check timestamp of last row vs current time?
    # Simple heuristic: look at the second to last row [-2] to be safe it's closed.
    # OR look at [-1] if we trust resampling cuts off correctly.
    # Let's use [-2] (Previous completed 15m period) to avoid exiting mid-candle.
    
    if len(df_15) < 2:
        return {'hit': False}
        
    last_completed = df_15.iloc[-2]
    
    close_price = last_completed['intc']
    ema_val = last_completed['EMA20']
    
    if pd.isna(ema_val):
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
