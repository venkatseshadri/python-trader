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

def analyze_icici_loss():
    stocks_dir = "python-trader/backtest_lab/data/stocks/"
    loader = DataLoader(os.path.join(stocks_dir, "ICICIBANK_minute.csv"))
    df = loader.load_data(days=20)
    
    # Prep 15m indicators
    df_15m = resample_data(df, 15)
    df_15m['e5_15m'] = talib.EMA(df_15m['close'].values.astype(float), 5)
    df_15m['e9_15m'] = talib.EMA(df_15m['close'].values.astype(float), 9)
    df = df.merge(df_15m[['date', 'e5_15m', 'e9_15m']], on='date', how='left').ffill()
    
    target_date = pd.to_datetime('2026-01-21').date()
    day_df = df[df['date'].dt.date == target_date].reset_index(drop=True)
    
    # Trade: 11:04 to 12:45
    mask = (day_df['date'].dt.time >= dt_time(11, 4)) & (day_df['date'].dt.time <= dt_time(12, 45))
    trade_df = day_df[mask]
    
    logs = []
    entry_price = 1340.50
    lot = 700
    for _, row in trade_df.iterrows():
        pnl = (entry_price - row['close']) * lot
        logs.append({
            'Time': row['date'].strftime('%H:%M'),
            'LTP': row['close'],
            'E5_15m': round(row['e5_15m'], 1),
            'E9_15m': round(row['e9_15m'], 1),
            'PnL': round(pnl, 0)
        })
        
    res = pd.DataFrame(logs)
    print("\n" + "="*80)
    print("🚩 FAILURE ANALYSIS: ICICIBANK SHORT (-Rs 10,290)")
    print("="*80)
    # Sample every 5 mins to see the trend
    print(res.iloc[::5].to_string(index=False))
    
    print("\nFinal Minute of Trade:")
    print(res.tail(1).to_string(index=False))

if __name__ == "__main__":
    analyze_icici_loss()
