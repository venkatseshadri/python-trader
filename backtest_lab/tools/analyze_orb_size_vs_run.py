import pandas as pd
import json
import os
import numpy as np

SUBSET_DIR = "backtest_lab/data/intraday1pct/"
OUTPUT_FILE = "backtest_lab/data/orb_size_vs_run.csv"

def analyze_size_impact():
    symbols = sorted([d for d in os.listdir(SUBSET_DIR) if os.path.isdir(os.path.join(SUBSET_DIR, d))])
    
    all_days = []
    print(f"🚀 Analyzing ORB Size impact for {len(symbols)} symbols...")

    for symbol in symbols:
        symbol_dir = os.path.join(SUBSET_DIR, symbol)
        json_files = [f for f in os.listdir(symbol_dir) if f.endswith(".json") and "_" in f]
        
        for f_name in json_files:
            try:
                with open(os.path.join(symbol_dir, f_name), 'r') as f:
                    candles = json.load(f)
                if len(candles) < 30: continue
                
                df = pd.DataFrame(candles)
                
                # 1. Base Prices
                prev_close = df.iloc[0]['open'] # Approximation for study
                orb_h, orb_l = df.iloc[:15]['high'].max(), df.iloc[:15]['low'].min()
                orb_size_pct = (orb_h - orb_l) / orb_l * 100
                
                # 2. Post-Break Run
                post_orb = df.iloc[15:]
                broken_h = post_orb[post_orb['high'] > orb_h]
                broken_l = post_orb[post_orb['low'] < orb_l]
                
                if not broken_h.empty or not broken_l.empty:
                    idx_h = broken_h.index[0] if not broken_h.empty else 9999
                    idx_l = broken_l.index[0] if not broken_l.empty else 9999
                    
                    if idx_h < idx_l: # LONG Break
                        max_p = post_orb.loc[idx_h:]['high'].max()
                        run_pct = (max_p - orb_h) / orb_h * 100
                    else: # SHORT Break
                        min_p = post_orb.loc[idx_l:]['low'].min()
                        run_pct = (orb_l - min_p) / orb_l * 100
                    
                    all_days.append({
                        "Symbol": symbol,
                        "ORB_Size_%": orb_size_pct,
                        "Post_Break_Run_%": run_pct
                    })
            except: pass

    if all_days:
        df_all = pd.DataFrame(all_days)
        
        # Define Buckets
        bins = [0, 0.25, 0.50, 0.75, 1.0, 5.0]
        labels = ['Very Small (<0.25%)', 'Small (0.25-0.5%)', 'Medium (0.5-0.75%)', 'Large (0.75-1%)', 'Extra Large (>1%)']
        df_all['ORB_Category'] = pd.cut(df_all['ORB_Size_%'], bins=bins, labels=labels)
        
        summary = df_all.groupby('ORB_Category', observed=True).agg({
            'Post_Break_Run_%': ['count', 'mean', 'median', 'max']
        })
        
        print("
📊 THE DYNAMIC TP PROOF: ORB SIZE vs. REMAINING ALPHA")
        print("-" * 85)
        print(summary.to_string())
        
        df_all.to_csv(OUTPUT_FILE, index=False)
        print(f"
✨ Raw data saved to: {OUTPUT_FILE}")

if __name__ == "__main__":
    analyze_size_impact()
