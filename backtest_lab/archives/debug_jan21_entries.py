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

def debug_jan21():
    stocks_dir = "python-trader/backtest_lab/data/stocks/"
    target_stock = "RELIANCE"
    loader = DataLoader(os.path.join(stocks_dir, f"{target_stock}_minute.csv"))
    df = loader.load_data(days=20)
    
    # 1. Indicators
    df_5m = resample_data(df, 5)
    df_5m['ema5_5m'] = talib.EMA(df_5m['close'].values.astype(float), 5)
    df_5m['ema9_5m'] = talib.EMA(df_5m['close'].values.astype(float), 9)
    df_5m['ema20_5m'] = talib.EMA(df_5m['close'].values.astype(float), 20)
    df_5m['ema50_5m'] = talib.EMA(df_5m['close'].values.astype(float), 50)
    
    df['adx'] = talib.ADX(df['high'].values.astype(float), df['low'].values.astype(float), df['close'].values.astype(float), 14)
    df = df.merge(df_5m[['date', 'ema5_5m', 'ema9_5m', 'ema20_5m', 'ema50_5m']], on='date', how='left').ffill()
    
    day_df = df[df['date'].dt.date == pd.to_datetime('2026-01-21').date()].reset_index(drop=True)
    
    # 2. ORB
    mask = (day_df['date'].dt.time >= dt_time(9, 15)) & (day_df['date'].dt.time <= dt_time(10, 0))
    orb_h = day_df.loc[mask, 'high'].max()
    orb_l = day_df.loc[mask, 'low'].min()
    
    print(f"DEBUG: {target_stock} Jan 21 | ORB High: {orb_h}, Low: {orb_l}")
    
    # 3. Minute-by-Minute check for the first 30 mins after ORB
    found = False
    for i in range(45, 100): # 10:00 to 10:55
        row = day_df.iloc[i]
        prev = day_df.iloc[i-1]
        t = row['date'].time()
        
        # Conditions
        is_breakout = row['close'] > orb_h or row['close'] < orb_l
        is_5m_aligned = row['ema5_5m'] > row['ema9_5m'] if row['close'] > orb_h else row['ema5_5m'] < row['ema9_5m']
        is_20_50_aligned = row['ema20_5m'] > row['ema50_5m'] if row['close'] > orb_h else row['ema20_5m'] < row['ema50_5m']
        is_adx_ok = row['adx'] > 20 and row['adx'] > prev['adx']
        
        if is_breakout:
            print(f"Time: {t} | LTP: {row['close']:.1f} | Breakout: {is_breakout} | 5m_5/9: {is_5m_aligned} | 5m_20/50: {is_20_50_aligned} | ADX_Rising: {is_adx_ok}")
            if is_breakout and is_5m_aligned and is_20_50_aligned and is_adx_ok:
                print(">>> ENTRY CRITERIA MET! <<<")
                found = True
                break
    
    if not found:
        print("Conclusion: Entry criteria never met simultaneously during this window.")

if __name__ == "__main__":
    debug_jan21()
