import argparse
import sys
import os
import pandas as pd
from datetime import time as dt_time

# Path fix
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

from backtest_lab.core.loader import DataLoader
from backtest_lab.core.optimizer import ScenarioManager

def run_risk_optimization(csv_path, days=250):
    loader = DataLoader(csv_path)
    full_df = loader.load_data()
    
    dates = full_df['date'].dt.date.unique()
    target_dates = dates[-days:]
    df = full_df[full_df['date'].dt.date.isin(target_dates)].copy()
    
    manager = ScenarioManager(loader, df)
    
    # --- DEFINE RISK SCENARIOS ---
    
    # 1. TSL Activation Sensitivity
    activations = [500, 1000, 2000]
    for act in activations:
        manager.run_scenario(f"TSL Act: Rs.{act}", {
            'tsl_activation_rs': act,
            'tsl_retracement_pct': 50
        })
        
    # 2. TSL Retracement Tightness
    retracements = [25, 50, 75]
    for ret in retracements:
        manager.run_scenario(f"TSL Retrace: {ret}%", {
            'tsl_activation_rs': 1000,
            'tsl_retracement_pct': ret
        })

    # 3. Soft ATR Exit Toggle
    manager.run_scenario("Soft SL: ATR enabled", {
        'soft_sl_atr': True
    })
    manager.run_scenario("Soft SL: ATR disabled", {
        'soft_sl_atr': False
    })

    # --- RESULTS ---
    summary = manager.get_summary()
    print("\n" + "="*70)
    print(f"🏆 RISK PARAMETER OPTIMIZATION (Last 250 Days)")
    print("="*70)
    print(summary.to_string(index=False))

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--csv', required=True)
    args = parser.parse_args()
    
    run_risk_optimization(args.csv, days=250)
