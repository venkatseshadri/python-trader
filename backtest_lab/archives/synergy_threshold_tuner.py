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

def run_threshold_study(csv_path, days=250):
    loader = DataLoader(csv_path)
    full_df = loader.load_data()
    
    dates = full_df['date'].dt.date.unique()
    target_dates = dates[-days:]
    df = full_df[full_df['date'].dt.date.isin(target_dates)].copy()
    
    manager = ScenarioManager(loader, df)
    
    # Entry: 50% Location (F2) + 50% Slope (F5)
    weights = [0.0, 0.5, 0.0, 0.0, 0.5, 0.0, 0.0]
    
    thresholds = [0.10, 0.15, 0.20, 0.25, 0.30]
    
    for t in thresholds:
        manager.run_scenario(f"Threshold: {t:.2f}", {
            'weights': weights,
            'trade_threshold': t,
            'sl_pct': 15.0,
            'tsl_retracement_pct': 50
        })

    # --- RESULTS ---
    summary = manager.get_summary()
    print("\n" + "="*70)
    print(f"🏆 SYNERGY THRESHOLD TUNING LEADERBOARD")
    print("="*70)
    print(summary.sort_values('ROI %', ascending=False).to_string(index=False))

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--csv', required=True)
    args = parser.parse_args()
    
    run_threshold_study(args.csv, days=250)
