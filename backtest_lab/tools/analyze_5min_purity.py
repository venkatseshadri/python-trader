import pandas as pd
import numpy as np
import talib
import os
import json

SUBSET_DIR = "backtest_lab/data/intraday1pct/"
STATS_FILE = "backtest_lab/data/nifty_volatility_stats.csv"
OUTPUT_FILE = "backtest_lab/data/5min_ema_purity.csv"

def count_breaks(df, ema_col, direction):
    if direction == 'LONG':
        breaks = (df['close'] < df[ema_col]) & (df['close'].shift(1) >= df[ema_col].shift(1))
    else:
        breaks = (df['close'] > df[ema_col]) & (df['close'].shift(1) <= df[ema_col].shift(1))
    return int(breaks.sum())

def analyze_5min_purity():
    df_stats = pd.read_csv(STATS_FILE)
    elite_symbols = df_stats[df_stats['Volatility_Frequency_%'] >= 95.0]['Symbol'].tolist()
    elite_symbols = [s for s in elite_symbols if s != 'ENRIN' and 'NIFTY' not in s]
    ema_periods = [5, 9, 20, 50, 100]
    results = []
    print(f"🚀 Analyzing 5-min Trend Purity for {len(elite_symbols)} stocks...")

    for symbol in elite_symbols:
        symbol_dir = os.path.join(SUBSET_DIR, symbol)
        if not os.path.exists(symbol_dir): continue
        json_files = [f for f in os.listdir(symbol_dir) if f.endswith(".json") and "_" in f]
        symbol_purity = {p: [] for p in ema_periods}
        for f_name in json_files:
            try:
                with open(os.path.join(symbol_dir, f_name), 'r') as f:
                    candles = json.load(f)
                if len(candles) < 150: continue
                df_1m = pd.DataFrame(candles)
                df_1m['date'] = pd.to_datetime(df_1m['date'])
                df_1m.set_index('date', inplace=True)
                direction = 'LONG' if df_1m.iloc[-1]['close'] > df_1m.iloc[0]['open'] else 'SHORT'
                df_5m = df_1m.resample('5min').agg({'open':'first','high':'max','low':'min','close':'last'}).dropna()
                for p in ema_periods:
                    if len(df_5m) < p + 5: continue
                    ema_col = f"ema{p}"
                    df_5m[ema_col] = talib.EMA(df_5m['close'].values.astype(float), timeperiod=p)
                    breaks = count_breaks(df_5m.dropna(), ema_col, direction)
                    symbol_purity[p].append(breaks)
            except: pass
        row = {"Symbol": symbol}
        for p in ema_periods:
            vals = symbol_purity[p]
            row[f"EMA{p}_Avg_Breaks"] = round(np.mean(vals), 2) if vals else None
        results.append(row)
        print(f"✅ {symbol}: Calculations complete.")

    if results:
        final_df = pd.DataFrame(results)
        final_df.to_csv(OUTPUT_FILE, index=False)
        summary = final_df.drop(columns=['Symbol']).mean()
        print("\n🏆 5-MIN TREND PURITY RANKING (Lowest Breaks = Best):")
        print("-" * 60)
        print(summary.sort_values().to_string())

if __name__ == "__main__":
    analyze_5min_purity()
