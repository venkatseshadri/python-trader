import pandas as pd
import numpy as np
import talib
import os
import sys
from datetime import datetime, time as dt_time

# Path fix
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))
from backtest_lab.core.loader import DataLoader
from backtest_lab.generate_golden_week import resample_data

def analyze_bosch_debacle():
    stocks_dir = "python-trader/backtest_lab/data/stocks/"
    loader = DataLoader(os.path.join(stocks_dir, "BOSCHLTD_minute.csv"))
    df = loader.load_data(days=30)
    
    # Prep Indicators
    df_15m = resample_data(df, 15)
    df_15m['ema5_15m'] = talib.EMA(df_15m['close'].values.astype(float), 5)
    df_15m['ema9_15m'] = talib.EMA(df_15m['close'].values.astype(float), 9)
    df_15m['ema20_15m'] = talib.EMA(df_15m['close'].values.astype(float), 20)
    df_15m['ema50_15m'] = talib.EMA(df_15m['close'].values.astype(float), 50)
    df_15m['adx_15m'] = talib.ADX(df_15m['high'].values.astype(float), df_15m['low'].values.astype(float), df_15m['close'].values.astype(float), 14)
    
    df = df.merge(df_15m[['date', 'ema5_15m', 'ema9_15m', 'ema20_15m', 'ema50_15m', 'adx_15m']], on='date', how='left').ffill()
    
    target_date = pd.to_datetime('2026-01-14').date()
    day_df = df[df['date'].dt.date == target_date].reset_index(drop=True)
    
    # Trade Trace (Assuming entry at 10:00 AM if filters match)
    entry_price = 0
    in_trade = False
    lot = 25
    trades = []
    
    for i, row in day_df.iterrows():
        t = row['date'].time()
        ltp = row['close']
        
        if not in_trade:
            # Check entry at 15m intervals
            if t.minute % 15 == 0 and t >= dt_time(10,0) and t <= dt_time(14,30):
                is_short = (row['ema5_15m'] < row['ema9_15m']) and (row['ema20_15m'] < row['ema50_15m']) and (row['adx_15m'] > 20)
                if is_short:
                    entry_price = ltp
                    in_trade = True
                    trades.append({'Time': row['date'], 'Action': 'ENTRY (SHORT)', 'Price': ltp, 'PnL': 0})
        else:
            pnl = (entry_price - ltp) * lot
            # Exit on 15m structural reversal
            if (row['ema5_15m'] > row['ema9_15m']) or t >= dt_time(15, 15):
                trades.append({'Time': row['date'], 'Action': 'EXIT', 'Price': ltp, 'PnL': pnl})
                in_trade = False
                
    print("\n" + "="*80)
    print(f"🕵️ BOSCHLTD DEBACLE AUDIT (Jan 14)")
    print("="*80)
    res = pd.DataFrame(trades)
    print(res.to_string(index=False))

if __name__ == "__main__":
    analyze_bosch_debacle()
