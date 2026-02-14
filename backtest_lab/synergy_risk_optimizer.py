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

def run_synergy_risk_study(csv_path, days=250):
    loader = DataLoader(csv_path)
    full_df = loader.load_data()
    
    dates = full_df['date'].dt.date.unique()
    target_dates = dates[-days:]
    df = full_df[full_df['date'].dt.date.isin(target_dates)].copy()
    
    manager = ScenarioManager(loader, df)
    
    # --- DEFINE SYNERGY RISK SCENARIOS ---
    weights = [0.0, 0.5, 0.0, 0.0, 0.5, 0.0, 0.0]
    
    sl_levels = [5.0, 10.0, 15.0, 20.0]
    activations = [500, 1000, 1500, 2000]
    retracements = [25, 50]
    
    print(f"🏗️ Launching Synergy Study: 32 Risk Variations...")

    for sl in sl_levels:
        for act in activations:
            for retrace in retracements:
                name = f"SL:{int(sl)}% | Act:Rs.{act} | Ret:{retrace}%"
                manager.run_scenario(name, {
                    'weights': weights,
                    'trade_threshold': 0.30,
                    'sl_pct': sl,
                    'tsl_activation_rs': act,
                    'tsl_retracement_pct': retrace
                })

    # --- RESULTS ---
    summary = manager.get_summary()
    print("\n" + "="*80)
    print(f"🏆 SYNERGY (F2+F5) RISK OPTIMIZATION LEADERBOARD")
    print("="*80)
    print(summary.sort_values('ROI %', ascending=False).to_string(index=False))

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--csv', required=True)
    args = parser.parse_args()
    
    run_synergy_risk_study(args.csv, days=250)
