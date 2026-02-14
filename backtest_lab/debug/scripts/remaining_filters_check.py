import argparse
import sys
import os
import pandas as pd

# Path fix
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from backtest_lab.core.loader import DataLoader
from backtest_lab.core.engine import BacktestEngine
from backtest_lab.core.optimizer import ScenarioManager

def run_remaining_filters(csv_path):
    loader = DataLoader(csv_path)
    full_df = loader.load_data()
    manager = ScenarioManager(loader, full_df)
    
    # Test each remaining filter solo
    filter_map = {
        3: "F3 (EMA Gap)",
        5: "F5 (EMA Scope/Slope)",
        6: "F6 (Gap Expansion)",
        7: "F7 (ATR Relative)"
    }
    
    for fid, name in filter_map.items():
        weights = [0.0]*7
        weights[fid-1] = 1.0
        manager.run_scenario(f"Solo: {name}", {
            'enabled_filters': [fid],
            'weights': weights,
            'trade_threshold': 0.01,
            'entry_start_time': "09:30"
        })

    summary = manager.get_summary()
    print("\n" + "="*70)
    print("🔬 REMAINING FILTERS PERFORMANCE ANALYSIS")
    print("="*70)
    print(summary.to_string(index=False))

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--csv', required=True)
    args = parser.parse_args()
    run_remaining_filters(args.csv)
