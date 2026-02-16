import pandas as pd
import numpy as np
import talib
import os
import sys
from datetime import datetime, time as dt_time

# Path fix
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))
from backtest_lab.core.loader import DataLoader
from backtest_lab.generate_golden_week import GoldenWeekEngine, resample_data

def debug_bosch_engine():
    stocks_dir = "python-trader/backtest_lab/data/stocks/"
    loader = DataLoader(os.path.join(stocks_dir, "BOSCHLTD_minute.csv"))
    df = loader.load_data(days=30)
    df_15m = resample_data(df, 15)
    df_15m['ema5_15m'], df_15m['ema9_15m'], df_15m['ema20_15m'], df_15m['ema50_15m'] = talib.EMA(df_15m['close'].values.astype(float), 5), talib.EMA(df_15m['close'].values.astype(float), 9), talib.EMA(df_15m['close'].values.astype(float), 20), talib.EMA(df_15m['close'].values.astype(float), 50)
    df_15m['adx_15m'] = talib.ADX(df_15m['high'].values.astype(float), df_15m['low'].values.astype(float), df_15m['close'].values.astype(float), 14)
    df = df.merge(df_15m[['date', 'ema5_15m', 'ema9_15m', 'ema20_15m', 'ema50_15m', 'adx_15m']], on='date', how='left').ffill()
    
    target_date = pd.to_datetime('2026-01-14').date()
    df_day = df[df['date'].dt.date == target_date].reset_index(drop=True)
    
    mask = (df_day['date'].dt.time >= dt_time(9, 15)) & (df_day['date'].dt.time <= dt_time(10, 0))
    df_day.attrs['orb'] = {'h': df_day.loc[mask, 'high'].max(), 'l': df_day.loc[mask, 'low'].min()}
    
    engine = GoldenWeekEngine(top_n=5)
    engine.run_simulation({"BOSCHLTD": df_day})
    
    print(f"🕵️ REPRODUCING BOSCHLTD: {target_date}")
    print(pd.DataFrame(engine.all_trades).to_string(index=False))

if __name__ == "__main__":
    debug_bosch_engine()
