import argparse
import sys
import os
import pandas as pd
from datetime import time as dt_time

# Path fix
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from backtest_lab.core.loader import DataLoader
from backtest_lab.core.engine import BacktestEngine
from backtest_lab.core.optimizer import ScenarioManager

def run_orb_solo(csv_path):
    loader = DataLoader(csv_path)
    full_df = loader.load_data()
    
    dates = full_df['date'].dt.date.unique()
    df = full_df.copy()
    
    manager = ScenarioManager(loader, df)
    
    # Solo F1 (ORB) starting at 9:30 AM
    manager.run_scenario("Solo: F1 (ORB) @ 09:30", {
        'enabled_filters': [1],
        'weights': [1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        'trade_threshold': 0.01,
        'entry_start_time': "09:30"
    })

    summary = manager.get_summary()
    print("\n" + "="*50)
    print("🎯 ORB SOLO PERFORMANCE ANALYSIS")
    print("="*50)
    print(summary.to_string(index=False))

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--csv', required=True)
    args = parser.parse_args()
    run_orb_solo(args.csv)
