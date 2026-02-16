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

def generate_lifecycle_log(stock_name, target_date_str, entry_t, exit_t):
    stocks_dir = "python-trader/backtest_lab/data/stocks/"
    loader = DataLoader(os.path.join(stocks_dir, f"{stock_name}_minute.csv"))
    df = loader.load_data(days=20)
    
    # Prep indicators
    df_5m = resample_data(df, 5)
    df_15m = resample_data(df, 15)
    df_15m['h2'] = df_15m['high'].rolling(2).max().shift(1)
    df_15m['l2'] = df_15m['low'].rolling(2).min().shift(1)
    df_5m['ema5_5m'] = talib.EMA(df_5m['close'].values.astype(float), 5)
    df_5m['ema9_5m'] = talib.EMA(df_5m['close'].values.astype(float), 9)
    df = df.merge(df_5m[['date', 'ema5_5m', 'ema9_5m']], on='date', how='left').ffill()
    df = df.merge(df_15m[['date', 'h2', 'l2']], on='date', how='left').ffill()
    
    # Filter for the trade window
    entry_dt = datetime.combine(pd.to_datetime(target_date_str).date(), dt_time(*map(int, entry_t.split(':'))))
    exit_dt = datetime.combine(pd.to_datetime(target_date_str).date(), dt_time(*map(int, exit_t.split(':'))))
    
    trade_df = df[(df['date'] >= entry_dt) & (df['date'] <= exit_dt)].copy()
    
    entry_price = trade_df['close'].iloc[0]
    lot = 250 # RELIANCE
    max_pnl = 0
    
    logs = []
    for _, row in trade_df.iterrows():
        pnl_pts = entry_price - row['close'] # SHORT
        pnl_rs = pnl_pts * lot
        max_pnl = max(max_pnl, pnl_rs)
        
        logs.append({
            'Time': row['date'].strftime('%H:%M'),
            'LTP': row['close'],
            'E5_5m': round(row['ema5_5m'], 1),
            'E9_5m': round(row['ema9_5m'], 1),
            '15m_High_2': row['h2'],
            'Current_PnL': round(pnl_rs, 0),
            'Max_PnL': round(max_pnl, 0)
        })
        
    res = pd.DataFrame(logs)
    print("\n" + "="*90)
    print(f"📊 LIFECYCLE LOG: {stock_name} SHORT on {target_date_str}")
    print("="*90)
    print(res.to_string(index=False))

if __name__ == "__main__":
    generate_lifecycle_log("RELIANCE", "2026-01-21", "10:23", "11:15")
