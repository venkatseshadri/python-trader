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

def run_f2_f5_study(csv_path, days=250):
    loader = DataLoader(csv_path)
    full_df = loader.load_data()
    
    dates = full_df['date'].dt.date.unique()
    target_dates = dates[-days:]
    df = full_df[full_df['date'].dt.date.isin(target_dates)].copy()
    
    manager = ScenarioManager(loader, df)
    
    # --- DEFINE F2 vs F5 COMBINATIONS ---
    proportions = [
        (1.0, 0.0), (0.9, 0.1), (0.8, 0.2), (0.7, 0.3), (0.6, 0.4), (0.5, 0.5),
        (0.4, 0.6), (0.3, 0.7), (0.2, 0.8), (0.1, 0.9), (0.0, 1.0)
    ]
    
    for f2_w, f5_w in proportions:
        weights = [0.0]*7
        weights[1] = f2_w
        weights[4] = f5_w
        
        manager.run_scenario(f"F2({int(f2_w*100)}%) + F5({int(f5_w*100)}%)", {
            'weights': weights,
            'trade_threshold': 0.30,
            'sl_pct': 15.0,
            'tsl_retracement_pct': 25
        })

    # --- RESULTS ---
    summary = manager.get_summary()
    print("\n" + "="*70)
    print(f"🏆 F2 (LOCATION) vs F5 (SLOPE) SYNERGY STUDY")
    print("="*70)
    print(summary.to_string(index=False))

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--csv', required=True)
    args = parser.parse_args()
    
    run_f2_f5_study(args.csv, days=250)
