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

def run_tuning(csv_path, days=250):
    loader = DataLoader(csv_path)
    full_df = loader.load_data()
    
    # Slice last 1 year
    dates = full_df['date'].dt.date.unique()
    target_dates = dates[-days:]
    df = full_df[full_df['date'].dt.date.isin(target_dates)].copy()
    
    manager = ScenarioManager(loader, df)
    
    # --- DEFINE TUNING SCENARIOS (F1-F4 ONLY) ---
    thresholds = [0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45]
    
    for t in thresholds:
        manager.run_scenario(f"F1-F4 | Threshold: {t:.2f}", {
            'enabled_filters': [1, 2, 3, 4],
            'trade_threshold': t
        })

    # --- RESULTS ---
    summary = manager.get_summary()
    print("\n" + "="*70)
    print(f"🏆 GOLDEN STACK (F1-F4) THRESHOLD TUNING (Last 250 Days)")
    print("="*70)
    print(summary.to_string(index=False))

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--csv', required=True)
    args = parser.parse_args()
    
    run_tuning(args.csv, days=250)
