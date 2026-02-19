import pandas as pd
import json
import os
import numpy as np

SUBSET_DIR = "backtest_lab/data/intraday1pct/"
OUTPUT_FILE = "backtest_lab/data/tp_probability_stats.csv"

def calculate_probabilities():
    symbols = sorted([d for d in os.listdir(SUBSET_DIR) if os.path.isdir(os.path.join(SUBSET_DIR, d))])
    results = []
    print(f"🚀 Calculating TP Hit Probabilities for {len(symbols)} symbols...")

    for symbol in symbols:
        symbol_dir = os.path.join(SUBSET_DIR, symbol)
        json_files = [f for f in os.listdir(symbol_dir) if f.endswith(".json") and "_" in f]
        total_breaks, hits_050, hits_075 = 0, 0, 0
        
        for f_name in json_files:
            try:
                with open(os.path.join(symbol_dir, f_name), 'r') as f:
                    candles = json.load(f)
                if len(candles) < 30: continue
                df = pd.DataFrame(candles)
                orb_h, orb_l = df.iloc[:15]['high'].max(), df.iloc[:15]['low'].min()
                post_orb = df.iloc[15:]
                broken_h = post_orb[post_orb['high'] > orb_h]
                broken_l = post_orb[post_orb['low'] < orb_l]
                
                if not broken_h.empty or not broken_l.empty:
                    total_breaks += 1
                    idx_h = broken_h.index[0] if not broken_h.empty else 9999
                    idx_l = broken_l.index[0] if not broken_l.empty else 9999
                    
                    if idx_h < idx_l:
                        max_price = post_orb.loc[idx_h:]['high'].max()
                        move = (max_price - orb_h) / orb_h * 100
                    else:
                        min_price = post_orb.loc[idx_l:]['low'].min()
                        move = (orb_l - min_price) / orb_l * 100
                    
                    if move >= 0.50: hits_050 += 1
                    if move >= 0.75: hits_075 += 1
            except: pass

        if total_breaks > 0:
            results.append({
                "Symbol": symbol, "Total_Breaks": total_breaks,
                "Prob_0.5%_Hit": round(hits_050 / total_breaks * 100, 2),
                "Prob_0.75%_Hit": round(hits_075 / total_breaks * 100, 2)
            })

    if results:
        final_df = pd.DataFrame(results).sort_values("Prob_0.75%_Hit", ascending=False)
        final_df.to_csv(OUTPUT_FILE, index=False)
        print(f"\n✨ TP Probability Table saved to: {OUTPUT_FILE}")
        print("\n🏆 TOP 15 STOCKS WITH HIGHEST 0.75% TP PROBABILITY:")
        print("-" * 75)
        print(final_df.head(15).to_string(index=False))

if __name__ == "__main__":
    calculate_probabilities()
