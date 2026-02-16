import argparse
import sys
import os
import pandas as pd
from datetime import time as dt_time

# Path fix
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))

from backtest_lab.core.loader import DataLoader
from backtest_lab.core.engine import BacktestEngine
from backtest_lab.core.optimizer import ScenarioManager

def run_combination_analysis(csv_path, days=250):
    loader = DataLoader(csv_path)
    full_df = loader.load_data()
    
    # Slice last 1 year
    dates = full_df['date'].dt.date.unique()
    target_dates = dates[-days:]
    df = full_df[full_df['date'].dt.date.isin(target_dates)].copy()
    
    manager = ScenarioManager(loader, df)
    
    # --- 1. BASELINE: No Filters (Enter on any 1m movement) ---
    manager.run_scenario("0. No Filters", {
        'enabled_filters': [],
        'trade_threshold': 0.00
    })

    # --- 2. SOLO RUNS: Test each filter individually ---
    filters = {
        1: "F1 (ORB)", 2: "F2 (EMA5 Loc)", 3: "F3 (EMA Gap)",
        4: "F4 (ST)", 5: "F5 (Scope)", 6: "F6 (Gap Exp)", 7: "F7 (ATR)"
    }
    for fid, name in filters.items():
        manager.run_scenario(f"Solo: {name}", {
            'enabled_filters': [fid],
            'trade_threshold': 0.05
        })

    # --- 3. ADDITIVE STACKS: 1, 1+2, 1+2+3... ---
    stack = []
    for fid in range(1, 8):
        stack.append(fid)
        if len(stack) > 1:
            name = "+".join([f"F{i}" for i in stack])
            manager.run_scenario(f"Stack: {name}", {
                'enabled_filters': list(stack),
                'trade_threshold': 0.15 # Higher threshold for combined signals
            })

    # --- RESULTS ---
    summary = manager.get_summary()
    print("\n" + "="*70)
    print(f"🏆 FILTER COMBINATION ANALYSIS (Last {days} Days)")
    print("="*70)
    print(summary.to_string(index=False))

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--csv', required=True)
    args = parser.parse_args()
    
    run_combination_analysis(args.csv, days=250)
