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

def run_weight_optimization(csv_path, days=250):
    loader = DataLoader(csv_path)
    full_df = loader.load_data()
    
    # Slice last 1 year
    dates = full_df['date'].dt.date.unique()
    target_dates = dates[-days:]
    df = full_df[full_df['date'].dt.date.isin(target_dates)].copy()
    
    manager = ScenarioManager(loader, df)
    
    # --- DEFINE WEIGHT SCENARIOS ---
    scenarios = {
        "1. Current Baseline": [1.0, 1.2, 1.2, 0.6, 1.2, 1.2, 1.0],
        "2. Uniform (Equal)":  [1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0],
        "3. Trend Heavy":      [0.5, 1.5, 1.0, 1.5, 0.5, 0.5, 1.0],
        "4. Momentum Heavy":   [0.5, 0.5, 1.0, 0.5, 2.0, 2.0, 1.0],
        "5. MVP (F3) Focus":   [0.5, 0.5, 3.0, 1.0, 0.5, 0.5, 1.0]
    }
    
    for name, weights in scenarios.items():
        manager.run_scenario(name, {
            'weights': weights,
            'trade_threshold': 0.30
        })

    # --- RESULTS ---
    summary = manager.get_summary()
    print("\n" + "="*75)
    print(f"🏆 WEIGHT PROPORTION OPTIMIZATION (Last 250 Days | Threshold 0.30)")
    print("="*75)
    print(summary.to_string(index=False))

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--csv', required=True)
    args = parser.parse_args()
    
    run_weight_optimization(args.csv, days=250)
