import pandas as pd
import numpy as np
import talib
import os
import sys
from datetime import datetime, time as dt_time

# Path fix
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))
from backtest_lab.core.loader import DataLoader

def get_snapshot_for_day(target_date_str, target_time_str):
    stocks_dir = "python-trader/backtest_lab/data/stocks/"
    # Get first 50 stocks
    all_files = sorted([f for f in os.listdir(stocks_dir) if f.endswith('_minute.csv')])
    target_stocks = all_files[:50]
    
    snapshot_time = dt_time(*map(int, target_time_str.split(':')))
    target_date = pd.to_datetime(target_date_str).date()
    
    results = []
    
    print(f"📡 Generating Selection Leaderboard for {target_date_str} at {target_time_str}...")
    
    for filename in target_stocks:
        stock_name = filename.replace('_minute.csv', '')
        loader = DataLoader(os.path.join(stocks_dir, filename))
        
        # Load enough data for indicators
        df = loader.load_data(days=5) 
        day_df = df[df['date'].dt.date == target_date].copy()
        
        if day_df.empty:
            continue
            
        # 1. ORB (9:15 - 10:00)
        orb_mask = (day_df['date'].dt.time >= dt_time(9, 15)) & (day_df['date'].dt.time <= dt_time(10, 0))
        orb_h = day_df.loc[orb_mask, 'high'].max()
        orb_l = day_df.loc[orb_mask, 'low'].min()
        
        # 2. Get specific minute row
        row_now = day_df[day_df['date'].dt.time == snapshot_time]
        if row_now.empty:
            continue
        
        idx = row_now.index[0]
        ltp = row_now['close'].values[0]
        
        # 3. Indicators (Calculate on the full slice for accuracy)
        closes = df['close'].values.astype(float)
        highs = df['high'].values.astype(float)
        lows = df['low'].values.astype(float)
        
        ema5 = talib.EMA(closes, 5)
        ema9 = talib.EMA(closes, 9)
        adx = talib.ADX(highs, lows, closes, 14)
        
        # Find the index in the 'df' (large slice) that matches our 'day_df' minute
        global_idx = df[df['date'] == row_now['date'].values[0]].index[0]
        
        # 4. Scoring (Weights: ORB=1.0, EMA_Gap=1.5, ADX=1.5)
        f1 = 0.25 if ltp > orb_h else (-0.25 if ltp < orb_l else 0)
        f3 = 0.20 if ema5[global_idx] > ema9[global_idx] else -0.20
        f8 = 0.25 if adx[global_idx] > 25 else 0
        
        total_score = (f1 * 1.0) + (f3 * 1.5) + (f8 * 1.5)
        
        results.append({
            'Stock': stock_name,
            'Price': ltp,
            'ORB_H': orb_h,
            'ORB_L': orb_l,
            'F1_ORB': f1,
            'F3_Gap': f3,
            'F8_ADX': f8,
            'Combined_Score': round(total_score, 3)
        })

    # RANKING
    df_res = pd.DataFrame(results)
    df_res['Abs_Score'] = df_res['Combined_Score'].abs()
    df_res = df_res.sort_values('Abs_Score', ascending=False).reset_index(drop=True)
    df_res['Rank'] = df_res.index + 1
    
    # SELECTION (Threshold 0.35, Top 5 slots)
    df_res['Selected'] = (df_res['Abs_Score'] >= 0.35) & (df_res['Rank'] <= 5)
    df_res['Selected'] = df_res['Selected'].map({True: '✅ YES', False: '❌ No'})

    # PRINT TOP 50
    print("\n" + "="*110)
    print(f"🏆 NIFTY 50 REAL-TIME LEADERBOARD | {target_date_str} {target_time_str}")
    print("="*110)
    print(df_res[['Rank', 'Stock', 'Price', 'F1_ORB', 'F3_Gap', 'F8_ADX', 'Combined_Score', 'Selected']].to_string(index=False))
    
    # MONTHLY PNL SUMMARY (Simulated logic for that day)
    # We could extend this to show how many of these Top 5 actually ended in profit
    
if __name__ == "__main__":
    generate_html = False # Keep simple CLI for now
    get_snapshot_for_day("2026-01-21", "10:05:00")
