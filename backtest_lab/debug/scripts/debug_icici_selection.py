import pandas as pd
import numpy as np
import talib
import os
import sys
from datetime import datetime, time as dt_time

# Path fix
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))
from backtest_lab.core.loader import DataLoader

def resample_data(df, interval_min):
    df = df.set_index('date')
    resampled = df.resample(f'{interval_min}min').agg({
        'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'
    }).dropna()
    return resampled.reset_index()

def debug_icici_audit():
    stocks_dir = "python-trader/backtest_lab/data/stocks/"
    loader = DataLoader(os.path.join(stocks_dir, "ICICIBANK_minute.csv"))
    df = loader.load_data(days=20)
    
    # Prep Indicators
    closes = df['close'].values.astype(float)
    df['ema20_15m'] = talib.EMA(closes, 300) # 15m * 20 = 300 min
    df['ema50_15m'] = talib.EMA(closes, 750) # 15m * 50 = 750 min
    
    df_15m = resample_data(df, 15)
    df_15m['e5'] = talib.EMA(df_15m['close'].values.astype(float), 5)
    df_15m['e9'] = talib.EMA(df_15m['close'].values.astype(float), 9)
    df_15m['adx'] = talib.ADX(df_15m['high'].values.astype(float), df_15m['low'].values.astype(float), df_15m['close'].values.astype(float), 14)
    
    df = df.merge(df_15m[['date', 'e5', 'e9', 'adx']], on='date', how='left').ffill()
    
    target_date = pd.to_datetime('2026-01-21').date()
    day_df = df[df['date'].dt.date == target_date].reset_index(drop=True)
    
    # ORB
    m_orb = (day_df['date'].dt.time >= dt_time(9, 15)) & (day_df['date'].dt.time <= dt_time(10, 0))
    orb_h = day_df.loc[m_orb, 'high'].max()
    orb_l = day_df.loc[m_orb, 'low'].min()
    
    print(f"🕵️ AUDIT: ICICIBANK Jan 21 | ORB Low: {orb_l}")
    print("="*110)
    print(f"{'Time':<8} | {'LTP':<8} | {'ADX':<6} | {'E5_15':<8} | {'E9_15':<8} | {'E20':<8} | {'E50':<8} | {'Status/Blocker'}")
    print("-" * 110)
    
    for i in range(45, 100): # 10:00 to 11:40
        row = day_df.iloc[i]
        t = row['date'].time()
        ltp = row['close']
        adx = row['adx']
        e5, e9 = row['e5'], row['e9']
        e20, e50 = row['ema20_15m'], row['ema50_15m']
        
        status = "OK"
        if t.minute % 15 != 0 and t != dt_time(11,0): 
            # We only evaluate at 15m intervals for entry
            status = "WAITING_15M_CLOSE"
        else:
            # Entry Evaluation
            if ltp >= orb_l: status = "NO_ORB_BREAKOUT"
            elif not (e5 < e9): status = "EMA5/9_NOT_BEARISH"
            elif not (e20 < e50): status = "EMA20/50_NOT_BEARISH"
            elif adx <= 20: status = "LOW_ADX"
            elif t == dt_time(11,0): status = ">>> ENTRY TAKEN <<<"
            
        print(f"{t} | {ltp:<8.1f} | {adx:<6.1f} | {e5:<8.1f} | {e9:<8.1f} | {e20:<8.1f} | {e50:<8.1f} | {status}")

if __name__ == "__main__":
    debug_icici_audit()
