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

def analyze_axis_institutional():
    stocks_dir = "python-trader/backtest_lab/data/stocks/"
    loader = DataLoader(os.path.join(stocks_dir, "AXISBANK_minute.csv"))
    df = loader.load_data(days=20)
    
    # 15m Prep
    df_15m = resample_data(df, 15)
    df_15m['e5'] = talib.EMA(df_15m['close'].values.astype(float), 5)
    df_15m['e9'] = talib.EMA(df_15m['close'].values.astype(float), 9)
    
    target_date = pd.to_datetime('2026-01-21').date()
    day_15m = df_15m[df_15m['date'].dt.date == target_date].reset_index(drop=True)
    
    print(f"🕵️ AUDITING AXISBANK (Jan 21) | 15m STRATEGY")
    print("="*90)
    print(f"{'Time':<10} | {'Close':<8} | {'E5_15m':<8} | {'E9_15m':<8} | {'Diff':<8} | {'Status'}")
    print("-" * 90)
    
    entry_price = 1282.40
    lot = 625
    
    for _, row in day_15m.iterrows():
        t = row['date'].strftime('%H:%M')
        c = row['close']
        e5, e9 = row['e5'], row['e9']
        diff = e5 - e9
        
        status = "IN_SHORT" if t > "10:00" and t < "12:45" else "SEARCHING"
        if t == "10:00": status = ">>> ENTRY <<<"
        if t == "12:45": status = ">>> EXIT (CROSSOVER) <<<"
        
        pnl = (entry_price - c) * lot if status != "SEARCHING" else 0
        
        print(f"{t:<10} | {c:<8.1f} | {e5:<8.1f} | {e9:<8.1f} | {diff:<8.2f} | {status} | PnL: {pnl:.0f}")

if __name__ == "__main__":
    analyze_axis_institutional()
