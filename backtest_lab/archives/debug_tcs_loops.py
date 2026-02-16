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

def debug_tcs_loops():
    stocks_dir = "python-trader/backtest_lab/data/stocks/"
    loader = DataLoader(os.path.join(stocks_dir, "TCS_minute.csv"))
    df = loader.load_data(days=20)
    
    # Prep indicators (Exactly as the Engine does)
    df_15m = resample_data(df, 15)
    df_15m['e5_15m'] = talib.EMA(df_15m['close'].values.astype(float), 5)
    df_15m['e9_15m'] = talib.EMA(df_15m['close'].values.astype(float), 9)
    df = df.merge(df_15m[['date', 'e5_15m', 'e9_15m']], on='date', how='left').ffill()
    
    # Filter for the problematic window: 10:00 to 11:30
    target_date = pd.to_datetime('2026-01-21').date()
    day_df = df[df['date'].dt.date == target_date].reset_index(drop=True)
    
    mask = (day_df['date'].dt.time >= dt_time(10, 0)) & (day_df['date'].dt.time <= dt_time(11, 30))
    debug_df = day_df[mask].copy()
    
    # ORB
    m_orb = (day_df['date'].dt.time >= dt_time(9, 15)) & (day_df['date'].dt.time <= dt_time(10, 0))
    orb_h = day_df.loc[m_orb, 'high'].max()
    
    print(f"🕵️ AUDITING TCS (Jan 21) | ORB High: {orb_h}")
    print("="*90)
    print(f"{'Time':<10} | {'LTP':<8} | {'E5_15m':<8} | {'E9_15m':<8} | {'Diff':<8} | {'Signal'}")
    print("-" * 90)
    
    for _, row in debug_df.iterrows():
        t = row['date'].strftime('%H:%M')
        ltp = row['close']
        e5, e9 = row['e5_15m'], row['e9_15m']
        diff = e5 - e9
        
        # Logic check
        is_breakout = ltp > orb_h
        is_bearish_reversal = e5 < e9
        
        status = "NORMAL"
        if is_breakout and not is_bearish_reversal: status = "ENTRY_ELIGIBLE"
        elif is_bearish_reversal: status = "EXIT_TRIGGERED"
        
        print(f"{t:<10} | {ltp:<8.1f} | {e5:<8.1f} | {e9:<8.1f} | {diff:<8.2f} | {status}")

if __name__ == "__main__":
    debug_tcs_loops()
