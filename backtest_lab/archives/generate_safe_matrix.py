import pandas as pd
import numpy as np
import talib
import os
import sys
from datetime import datetime, time as dt_time

# Path fix
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))
from backtest_lab.core.loader import DataLoader
from backtest_lab.generate_ultra_matrix import UltraDefenseEngine, resample_data, LOT_SIZES

def generate_safe_matrix():
    stocks_dir = "python-trader/backtest_lab/data/stocks/"
    # EXCLUDING HIGH-NOISE STOCKS
    top_stocks = ["RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK", "SBIN", "LT", "AXISBANK", "BHARTIARTL", "KOTAKBANK", "ABB", "ADANIENT", "ASIANPAINT", "BAJFINANCE"]
    
    sample_df = pd.read_csv(os.path.join(stocks_dir, "RELIANCE_minute.csv"))
    all_dates = sorted(pd.to_datetime(sample_df['date']).dt.date.unique())[-7:]
    
    matrix_data = {s: {d.strftime('%d-%b'): 0 for d in all_dates} for s in top_stocks}
    engine = UltraDefenseEngine(top_n=5)
    
    for d in all_dates:
        print(f"▶️ Simulating: {d}")
        stock_data_day = {}
        for s in top_stocks:
            loader = DataLoader(os.path.join(stocks_dir, f"{s}_minute.csv"))
            df = loader.load_data(days=20)
            
            # ATR FILTER (Purity Check)
            df['atr'] = talib.ATR(df['high'].values.astype(float), df['low'].values.astype(float), df['close'].values.astype(float), 14)
            avg_price = df['close'].mean()
            avg_atr = df['atr'].mean()
            
            # If volatility is too high relative to price, skip this stock entirely
            if (avg_atr / avg_price) > 0.008: 
                # print(f"⚠️ Skipping {s} (High Volatility: {avg_atr/avg_price:.4f})")
                continue

            df_5m, df_15m = resample_data(df, 5), resample_data(df, 15)
            df_5m['ema5_5m'] = talib.EMA(df_5m['close'].values.astype(float), 5)
            df_15m['ema5_15m'], df_15m['ema9_15m'], df_15m['ema20_15m'], df_15m['ema50_15m'] = talib.EMA(df_15m['close'].values.astype(float), 5), talib.EMA(df_15m['close'].values.astype(float), 9), talib.EMA(df_15m['close'].values.astype(float), 20), talib.EMA(df_15m['close'].values.astype(float), 50)
            df_15m['adx_15m'] = talib.ADX(df_15m['high'].values.astype(float), df_15m['low'].values.astype(float), df_15m['close'].values.astype(float), 14)
            df = df.merge(df_5m[['date', 'ema5_5m']], on='date', how='left').ffill()
            df = df.merge(df_15m[['date', 'ema5_15m', 'ema9_15m', 'ema20_15m', 'ema50_15m', 'adx_15m']], on='date', how='left').ffill()
            df_day = df[df['date'].dt.date == d].reset_index(drop=True)
            if df_day.empty: continue
            mask = (df_day['date'].dt.time >= dt_time(9, 15)) & (df_day['date'].dt.time <= dt_time(10, 0))
            df_day.attrs['orb'] = {'h': df_day.loc[mask, 'high'].max(), 'l': df_day.loc[mask, 'low'].min()}
            stock_data_day[s] = df_day
        
        engine.run_simulation(stock_data_day)
        for t in engine.all_trades:
            if t['Stock'] in matrix_data:
                matrix_data[t['Stock']][d.strftime('%d-%b')] += t['PnL_Rs']
        engine.all_trades = []

    df_matrix = pd.DataFrame.from_dict(matrix_data, orient='index')
    df_matrix['Total'] = df_matrix.sum(axis=1)
    df_matrix.to_html("python-trader/backtest_lab/reports/safe_portfolio_matrix.html")
    print(f"✅ Safe Matrix generated: python-trader/backtest_lab/reports/safe_portfolio_matrix.html")

if __name__ == "__main__":
    generate_safe_matrix()
