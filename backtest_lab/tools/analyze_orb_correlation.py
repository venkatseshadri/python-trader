import pandas as pd
import json
import os
import numpy as np

SUBSET_DIR = "backtest_lab/data/intraday1pct/"
SOURCE_DIR = "backtest_lab/data/stocks/"
OUTPUT_FILE = "backtest_lab/data/orb_convergence_study.csv"

def analyze_convergence():
    symbols = sorted([d for d in os.listdir(SUBSET_DIR) if os.path.isdir(os.path.join(SUBSET_DIR, d))])
    
    print(f"🚀 Running ORB vs 1% Convergence Study for {len(symbols)} symbols...")

    results = []

    for symbol in symbols:
        symbol_dir = os.path.join(SUBSET_DIR, symbol)
        source_csv = os.path.join(SOURCE_DIR, f"{symbol}_minute.csv")
        if not os.path.exists(source_csv): continue
        
        try:
            # 1. Total Traded Days
            df_dates = pd.read_csv(source_csv, usecols=['date'])
            total_traded_days = pd.to_datetime(df_dates['date']).dt.date.nunique()
            
            # 2. Days with > 1% Move (The Subset)
            json_files = [f for f in os.listdir(symbol_dir) if f.endswith(".json") and "_" in f]
            volatile_days_count = len(json_files)
            
            # 3. Analyze each 1% day for an ORB break
            breaks_on_volatile_days = 0
            
            for f_name in json_files:
                with open(os.path.join(symbol_dir, f_name), 'r') as f:
                    candles = json.load(f)
                if len(candles) < 20: continue
                
                df = pd.DataFrame(candles)
                orb_h, orb_l = df.iloc[:15]['high'].max(), df.iloc[:15]['low'].min()
                
                # Check for break ANYWHERE after 15 mins
                post_orb = df.iloc[15:]
                if (post_orb['high'] > orb_h).any() or (post_orb['low'] < orb_l).any():
                    breaks_on_volatile_days += 1

            # 4. Calculate Convergence
            heartbeat_pct = (volatile_days_count / total_traded_days * 100)
            orb_hit_rate_on_1pct = (breaks_on_volatile_days / volatile_days_count * 100) if volatile_days_count > 0 else 0
            
            results.append({
                "Symbol": symbol,
                "Total_Days": total_traded_days,
                "Volatile_Days_1pct": volatile_days_count,
                "Heartbeat_%": round(heartbeat_pct, 2),
                "ORB_Breaks_on_1pct_Days": breaks_on_volatile_days,
                "ORB_Capture_Rate_%": round(orb_hit_rate_on_1pct, 2)
            })
            
            print(f"✅ {symbol}: {volatile_days_count} volatile days | ORB captured {orb_hit_rate_on_1pct:.1f}%")

        except Exception as e:
            print(f"❌ Error {symbol}: {e}")

    if results:
        final_df = pd.DataFrame(results).sort_values("ORB_Capture_Rate_%", ascending=False)
        final_df.to_csv(OUTPUT_FILE, index=False)
        print(f"\n✨ Convergence Study saved to: {OUTPUT_FILE}")
        
        print("\n🏆 TOP 15 STOCKS WHERE ORB BEST CAPTURES 1% MOVES:")
        print("-" * 100)
        print(final_df.head(15).to_string(index=False))

if __name__ == "__main__":
    analyze_convergence()
