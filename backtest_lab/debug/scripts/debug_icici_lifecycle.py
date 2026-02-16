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

def debug_icici_lifecycle():
    stocks_dir = "python-trader/backtest_lab/data/stocks/"
    loader = DataLoader(os.path.join(stocks_dir, "ICICIBANK_minute.csv"))
    df = loader.load_data(days=20)
    
    # 1. Prepare Indicators
    closes = df['close'].values.astype(float)
    df['ema5_1m'] = talib.EMA(closes, 5)
    df['ema9_1m'] = talib.EMA(closes, 9)
    
    df_15m = resample_data(df, 15)
    df_15m['ema5_15m'] = talib.EMA(df_15m['close'].values.astype(float), 5)
    df_15m['ema9_15m'] = talib.EMA(df_15m['close'].values.astype(float), 9)
    
    # Merge 15m indicators back to 1m
    df = df.merge(df_15m[['date', 'ema5_15m', 'ema9_15m']], on='date', how='left').ffill()
    
    # 2. Filter for the trade: 2026-01-21, 11:00 to 11:51
    target_date = pd.to_datetime('2026-01-21').date()
    mask = (df['date'].dt.date == target_date) & (df['date'].dt.time >= dt_time(11, 0)) & (df['date'].dt.time <= dt_time(11, 51))
    trade_df = df[mask].copy()
    
    entry_price = 1341.40
    lot = 700 # ICICIBANK
    max_pnl = 0
    
    logs = []
    for _, row in trade_df.iterrows():
        # Short PnL = (Entry - LTP) * Lot
        pnl = (entry_price - row['close']) * lot
        max_pnl = max(max_pnl, pnl)
        
        logs.append({
            'Time': row['date'].strftime('%H:%M'),
            'LTP': row['close'],
            'EMA5_1m': round(row['ema5_1m'], 1),
            'EMA9_1m': round(row['ema9_1m'], 1),
            'EMA5_15m': round(row['ema5_15m'], 1),
            'EMA9_15m': round(row['ema9_15m'], 1),
            'PnL_Rs': round(pnl, 0),
            'Max_PnL': round(max_pnl, 0)
        })
        
    res = pd.DataFrame(logs)
    print("\n" + "="*100)
    print(f"📊 MINUTE-BY-MINUTE LOG: ICICIBANK SHORT (Jan 21)")
    print("="*100)
    print(res.to_string(index=False))

if __name__ == "__main__":
    debug_icici_lifecycle()
