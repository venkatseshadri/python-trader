import pandas as pd
import numpy as np
import talib
import os
import sys
from datetime import datetime, time as dt_time

# Path fix
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))
from backtest_lab.core.loader import DataLoader
from backtest_lab.adx_one_year_study import ADXExtendedEngine, calc_stats

# Use the same MegaEngine but for solo filter testing
from backtest_lab.mega_stock_optimizer import MegaEngine

def run_filter_isolation():
    stocks_dir = "python-trader/backtest_lab/data/stocks/"
    top_stocks = ["RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK", "BHARTIARTL", "SBIN", "LT", "AXISBANK", "KOTAKBANK"]
    stock_files = [os.path.join(stocks_dir, f"{s}_minute.csv") for s in top_stocks]
    
    filters = {
        0: "F1 (ORB)", 1: "F2 (EMA5 Loc)", 2: "F3 (EMA Gap)",
        3: "F4 (ST)", 4: "F5 (Scope)", 5: "F6 (Gap Exp)",
        6: "F7 (ATR)", 7: "F8 (ADX Sniper)"
    }
    
    results = []
    
    # 90 days for speed
    days_to_test = 90
    
    print(f"🧪 Running Filter Isolation on {len(top_stocks)} stocks...")
    
    for fid, fname in filters.items():
        print(f"▶️ Testing Solo: {fname}...")
        
        # Test 3 weight levels for each solo filter
        for w_val in [1.0, 5.0, 10.0]:
            weights = [0.0] * 8
            weights[fid] = w_val
            
            engine = MegaEngine(None, config={
                'weights': weights, 'trade_threshold': 0.1 * w_val, # Proportionate threshold
                'sl_pct': 10, 'tsl_retracement_pct': 30,
                'tsl_activation_rs': 1000
            })
            
            summary_df = engine.run_multi_stock(stock_files, days=days_to_test)
            avg_roi = summary_df['PnL'].sum() * 50 / (100000 * len(top_stocks)) * 100
            avg_wr = summary_df['Win%'].mean()
            
            results.append({
                'Filter': fname, 'Weight': w_val, 'Avg ROI%': avg_roi, 'Avg Win%': avg_wr, 'Trades': summary_df['Trades'].sum()
            })

    res_df = pd.DataFrame(results).sort_values('Avg ROI%', ascending=False)
    print("\n" + "="*80)
    print("🏆 SOLO FILTER PERFORMANCE (TOP 10 STOCKS)")
    print("="*80)
    print(res_df.to_string(index=False))

if __name__ == "__main__":
    run_filter_isolation()
