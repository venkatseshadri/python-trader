import pandas as pd
import numpy as np
import talib
import os
import json
from datetime import datetime

SUBSET_DIR = "backtest_lab/data/intraday1pct/"
STATS_FILE = "backtest_lab/data/nifty_volatility_stats.csv"
OUTPUT_FILE = "backtest_lab/data/ema_recovery_study.csv"

def analyze_recovery():
    df_stats = pd.read_csv(STATS_FILE)
    elite_symbols = df_stats[df_stats['Volatility_Frequency_%'] >= 95.0]['Symbol'].tolist()
    elite_symbols = [s for s in elite_symbols if s != 'ENRIN' and 'NIFTY' not in s]
    ema_periods = [9, 20, 50]
    timeframes = ['5min', '15min']
    results = []
    print(f"🚀 Analyzing EMA Recovery (False Dips) for {len(elite_symbols)} stocks...")

    for symbol in elite_symbols:
        symbol_dir = os.path.join(SUBSET_DIR, symbol)
        if not os.path.exists(symbol_dir): continue
        json_files = [f for f in os.listdir(symbol_dir) if f.endswith(".json") and "_" in f]
        stats = {tf: {p: {"total": 0, "recovered": 0} for p in ema_periods} for tf in timeframes}
        for f_name in json_files:
            try:
                with open(os.path.join(symbol_dir, f_name), 'r') as f:
                    candles = json.load(f)
                if len(candles) < 100: continue
                df_1m = pd.DataFrame(candles)
                df_1m['date'] = pd.to_datetime(df_1m['date'])
                df_1m.set_index('date', inplace=True)
                eod_close = df_1m.iloc[-1]['close']
                direction = 'LONG' if eod_close > df_1m.iloc[0]['open'] else 'SHORT'
                for tf in timeframes:
                    df_tf = df_1m.resample(tf).agg({'open':'first','high':'max','low':'min','close':'last'}).dropna()
                    for p in ema_periods:
                        if len(df_tf) < p + 5: continue
                        ema_col = f"ema{p}"
                        df_tf[ema_col] = talib.EMA(df_tf['close'].values.astype(float), timeperiod=p)
                        temp_df = df_tf.dropna()
                        if direction == 'LONG': breaches = temp_df[temp_df['close'] < temp_df[ema_col]]
                        else: breaches = temp_df[temp_df['close'] > temp_df[ema_col]]
                        if not breaches.empty:
                            stats[tf][p]["total"] += len(breaches)
                            if direction == 'LONG' and eod_close > temp_df[ema_col].iloc[-1]: stats[tf][p]["recovered"] += len(breaches)
                            elif direction == 'SHORT' and eod_close < temp_df[ema_col].iloc[-1]: stats[tf][p]["recovered"] += len(breaches)
            except: pass
        for tf in timeframes:
            for p in ema_periods:
                s = stats[tf][p]
                recovery_rate = (s["recovered"] / s["total"] * 100) if s["total"] > 0 else 0
                results.append({"Symbol": symbol, "TF": tf, "EMA": p, "Total_Breaches": s["total"], "Recovery_Rate_%": round(recovery_rate, 2)})
        print(f"✅ {symbol}: Recovery analysis complete.")

    if results:
        final_df = pd.DataFrame(results)
        final_df.to_csv(OUTPUT_FILE, index=False)
        summary = final_df.groupby(['TF', 'EMA']).agg({'Recovery_Rate_%': 'mean'})
        print("\n🏆 EMA RECOVERY RANKING (Higher % = Safer to ignore the dip):")
        print("-" * 65)
        print(summary.sort_values('Recovery_Rate_%', ascending=False).to_string())

if __name__ == "__main__":
    analyze_recovery()
