import pandas as pd
import numpy as np
import talib
import os
import json
from datetime import datetime

SUBSET_DIR = "backtest_lab/data/intraday1pct/"
STATS_FILE = "backtest_lab/data/nifty_volatility_stats.csv"
OUTPUT_FILE = "backtest_lab/data/ema_noise_study.csv"

def count_breaks(df, ema_col, direction):
    if direction == 'LONG':
        breaks = (df['close'] < df[ema_col]) & (df['close'].shift(1) >= df[ema_col].shift(1))
    else:
        breaks = (df['close'] > df[ema_col]) & (df['close'].shift(1) <= df[ema_col].shift(1))
    return breaks.sum()

def analyze_ema_purity():
    df_stats = pd.read_csv(STATS_FILE)
    elite_symbols = df_stats[df_stats['Volatility_Frequency_%'] >= 95.0]['Symbol'].tolist()
    elite_symbols = [s for s in elite_symbols if s != 'ENRIN' and 'NIFTY' not in s]
    print(f"🚀 Analyzing EMA Noise for {len(elite_symbols)} stocks...")
    ema_periods = [5, 9, 20, 50, 100]
    timeframes = ['5min', '15min', '60min']
    results = []

    for symbol in elite_symbols:
        symbol_dir = os.path.join(SUBSET_DIR, symbol)
        if not os.path.exists(symbol_dir): continue
        json_files = [f for f in os.listdir(symbol_dir) if f.endswith(".json") and "_" in f]
        symbol_stats = {}
        for tf in timeframes:
            for p in ema_periods:
                symbol_stats[f"{tf}_EMA{p}_Breaks"] = []

        for f_name in json_files:
            try:
                with open(os.path.join(symbol_dir, f_name), 'r') as f:
                    candles = json.load(f)
                if len(candles) < 60: continue
                df_1m = pd.DataFrame(candles)
                df_1m['date'] = pd.to_datetime(df_1m['date'])
                df_1m.set_index('date', inplace=True)
                direction = 'LONG' if df_1m.iloc[-1]['close'] > df_1m.iloc[0]['open'] else 'SHORT'
                for tf in timeframes:
                    df_tf = df_1m.resample(tf).agg({'open':'first','high':'max','low':'min','close':'last'}).dropna()
                    for p in ema_periods:
                        if len(df_tf) < p: continue
                        ema_col = f"ema{p}"
                        df_tf[ema_col] = talib.EMA(df_tf['close'].values.astype(float), timeperiod=p)
                        breaks = count_breaks(df_tf.dropna(), ema_col, direction)
                        symbol_stats[f"{tf}_EMA{p}_Breaks"].append(breaks)
            except: pass

        row = {"Symbol": symbol, "Days": len(json_files)}
        for key, vals in symbol_stats.items():
            if vals: row[key] = round(np.mean(vals), 2)
            else: row[key] = None
        results.append(row)
        print(f"✅ {symbol}: Processed {len(json_files)} sessions.")

    if results:
        final_df = pd.DataFrame(results)
        final_df.to_csv(OUTPUT_FILE, index=False)
        print(f"\n✨ EMA Noise Study saved to: {OUTPUT_FILE}")
        avg_breaks = final_df.drop(columns=['Symbol', 'Days']).mean()
        print("\n🏆 GLOBAL NOISE RANKING (Avg Breaks per Session):")
        print("-" * 50)
        print(avg_breaks.sort_values().to_string())

if __name__ == "__main__":
    analyze_ema_purity()
