import pandas as pd
import numpy as np
from datetime import datetime, time as dt_time

REVAMP_FILE = "backtest_lab/orbiter_revamp_data.csv"
OUTPUT_FILE = "backtest_lab/data/reversal_pattern_study.csv"

def get_bucket_from_time(time_str):
    if not time_str or time_str == 'N/A': return "None"
    try:
        t = datetime.strptime(str(time_str), "%H:%M").time()
        if t < dt_time(10, 30): return "B1"
        if t < dt_time(12, 0): return "B2"
        if t < dt_time(13, 30): return "B3"
        return "B4"
    except: return "None"

def analyze_reversals():
    df = pd.read_csv(REVAMP_FILE)
    df_gap = df[df['Gap%'].abs() > 0.5].copy()
    print(f"🚀 Analyzing Reversal Patterns for {len(df_gap)} High-Gap events...")

    def calc_run(row):
        d_open = row['Prev_Close'] * (1 + row['Gap%']/100)
        if row['Gap%'] > 0:
            return (row['Swing_High'] - d_open) / d_open * 100
        else:
            return (d_open - row['Swing_Low']) / d_open * 100

    df_gap['Run_After_Gap_%'] = df_gap.apply(calc_run, axis=1)
    df_gap['PB_Bucket'] = df_gap['PB_Time'].apply(get_bucket_from_time)
    
    summary = df_gap.groupby('PB_Bucket', observed=True).agg({
        'Run_After_Gap_%': ['mean', 'median'],
        'PB_Depth%': ['mean', 'count'],
        'Is_Reversal': 'sum'
    })
    print("\n📊 REVERSAL TIMING & MAGNITUDE (On High-Gap Days):")
    print("-" * 80)
    print(summary.to_string())
    
    mover_source = df_gap['Best_Bucket'].value_counts(normalize=True) * 100
    print("\n🏆 SOURCE OF 1% MOVE (Which bucket delivered the alpha?):")
    for bucket, freq in mover_source.items():
        print(f"  {bucket}: {freq:.1f}% of mover days")

    def check_negation(row):
        if row['Gap%'] > 0 and row['Total_Move%'] < 0: return True
        if row['Gap%'] < 0 and row['Total_Move%'] > 0: return True
        return False
    
    negation_rate = df_gap.apply(check_negation, axis=1).mean() * 100
    print(f"\n💀 GAP NEGATION RATE: {negation_rate:.1f}%")
    df_gap.to_csv(OUTPUT_FILE, index=False)

if __name__ == "__main__":
    analyze_reversals()
