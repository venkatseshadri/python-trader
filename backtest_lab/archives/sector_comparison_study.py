import pandas as pd
import numpy as np
import talib
import os
import sys
from datetime import datetime

# Path fix
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))
from backtest_lab.core.loader import DataLoader
from backtest_lab.core.engine import BacktestEngine
from backtest_lab.adx_one_year_study import ADXExtendedEngine, calc_stats

def run_sector_comparison():
    source_dir = "/Users/vseshadri/tmp/nifty 50 - archive/"
    targets = [
        "NIFTY 50_minute.csv",
        "NIFTY BANK_minute.csv",
        "NIFTY IT_minute.csv",
        "NIFTY AUTO_minute.csv"
    ]
    
    # Using the optimized F8 Sniper settings: ADX > 25, Weight 1.0, Score Threshold 0.35
    sa_weights = [0.5, 1.0, 0.5, 0.5, 0.8, 1.2, 0.7]
    
    results = []
    
    for filename in targets:
        csv_path = os.path.join(source_dir, filename)
        if not os.path.exists(csv_path):
            print(f"Skipping {filename} (not found)")
            continue
            
        print(f"🚀 Simulating {filename}...")
        loader = DataLoader(csv_path)
        df = loader.load_data(days=180) # 6 months for speed
        dates = sorted(df['date'].dt.date.unique())
        
        # We test two SL variations to answer your "How much should I tweak" question
        for sl_val in [10, 15]:
            engine = ADXExtendedEngine(loader, adx_threshold=25, 
                                      config={'weights': sa_weights, 'trade_threshold': 0.35, 'sl_pct': sl_val})
            
            for d in dates:
                df_day = df[df['date'].dt.date == d].copy()
                engine.run_day(df_day)
                engine.finalize_day(d)
                
            roi, pf, count, dd = calc_stats(engine.trades, engine.daily_stats)
            results.append({
                'Asset': filename.replace('_minute.csv', ''),
                'SL %': sl_val,
                'ROI %': roi,
                'PF': pf,
                'Trades': count,
                'Max DD %': dd
            })

    res_df = pd.DataFrame(results)
    print("\n" + "="*80)
    print("SECTOR COMPARISON & SL SENSITIVITY")
    print("="*80)
    print(res_df.to_string(index=False))

if __name__ == "__main__":
    run_sector_comparison()
