import pandas as pd
import numpy as np
import talib
import os
import sys
from datetime import datetime, time as dt_time
import itertools

# Path fix
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))
from backtest_lab.core.loader import DataLoader
from backtest_lab.mega_stock_optimizer import MegaEngine

def run_selective_sniper_optimization():
    stocks_dir = "python-trader/backtest_lab/data/stocks/"
    top_stocks = ["RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK", "BHARTIARTL", "SBIN", "LT", "AXISBANK", "KOTAKBANK"]
    stock_files = [os.path.join(stocks_dir, f"{s}_minute.csv") for s in top_stocks]
    
    # 1. SNIPER CONFIGS (Focusing on F3 and F8)
    # Weights: [F1, F2, F3, F4, F5, F6, F7, F8]
    # We will test variations of F3 and F8 only
    configs = [
        ("F3 Focus", [0, 0, 5.0, 0, 0, 0, 0, 0], 0.5),
        ("F3+F8 Sniper", [0, 0, 5.0, 0, 0, 0, 0, 5.0], 1.0),
        ("F3+F8 Strict", [0, 0, 10.0, 0, 0, 0, 0, 10.0], 2.5),
    ]
    
    sl_vals = [5, 10, 15]
    tsl_retracement_vals = [20, 30, 40]
    
    combinations = list(itertools.product(configs, sl_vals, tsl_retracement_vals))
    
    print(f"🧪 Running Sniper Optimization: {len(combinations)} parameter sets...")
    
    master_results = []
    
    for (name, weights, thr), sl, tsl_r in combinations:
        engine = MegaEngine(None, config={
            'weights': weights, 'trade_threshold': thr, 
            'sl_pct': sl, 'tsl_retracement_pct': tsl_r,
            'tsl_activation_rs': 500 # Lower activation for stocks
        })
        
        summary_df = engine.run_multi_stock(stock_files, days=90)
        
        avg_roi = summary_df['PnL'].sum() * 50 / (100000 * len(top_stocks)) * 100
        avg_wr = summary_df['Win%'].mean()
        total_trades = summary_df['Trades'].sum()
        
        print(f"Tested: {name} | SL: {sl}% | TSL-R: {tsl_r}% -> ROI: {avg_roi:.2f}%")
        
        master_results.append({
            'Config': name, 'SL': sl, 'TSL-R': tsl_r,
            'Avg ROI%': avg_roi, 'Avg Win%': avg_wr, 'Total Trades': total_trades
        })

    master_df = pd.DataFrame(master_results).sort_values('Avg ROI%', ascending=False)
    print("\n" + "="*80)
    print("🏆 SNIPER OPTIMIZATION SUMMARY")
    print("="*80)
    print(master_df.head(10).to_string(index=False))

if __name__ == "__main__":
    run_selective_sniper_optimization()
