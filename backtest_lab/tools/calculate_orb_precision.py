import pandas as pd
import numpy as np
import os

SOURCE_DIR = "backtest_lab/data/stocks/"
OUTPUT_FILE = "backtest_lab/data/orb_precision_stats.csv"

def calculate_precision():
    all_files = sorted([f for f in os.listdir(SOURCE_DIR) if f.endswith("_minute.csv")])
    results = []
    print(f"🚀 Calculating Clean ORB Precision & Reliability for {len(all_files)} stocks...")

    for f_name in all_files:
        symbol = f_name.replace("_minute.csv", "")
        file_path = os.path.join(SOURCE_DIR, f_name)
        try:
            df = pd.read_csv(file_path, usecols=['date', 'high', 'low', 'close'])
            df['date'] = pd.to_datetime(df['date'])
            days = df.groupby(df['date'].dt.date)
            
            total_1pct_days, total_orb_breaks, successful_breaks = 0, 0, 0
            
            for day, day_df in days:
                if len(day_df) < 30: continue
                
                d_high, d_low = day_df['high'].max(), day_df['low'].min()
                # 🛡️ Fix: Filter out zero or garbage prices to avoid RuntimeWarnings
                if d_low <= 1.0 or pd.isna(d_low): continue
                
                is_1pct_day = (d_high - d_low) / d_low * 100 >= 1.0
                if is_1pct_day: total_1pct_days += 1
                
                orb_df = day_df.iloc[:15]
                orb_h, orb_l = orb_df['high'].max(), orb_df['low'].min()
                if orb_h == 0 or orb_l == 0: continue
                
                post_orb = day_df.iloc[15:]
                has_break = (post_orb['high'] > orb_h).any() or (post_orb['low'] < orb_l).any()
                
                if has_break:
                    total_orb_breaks += 1
                    if is_1pct_day: successful_breaks += 1
            
            reliability = (successful_breaks / total_1pct_days) if total_1pct_days > 0 else 0
            precision = (successful_breaks / total_orb_breaks) if total_orb_breaks > 0 else 0
            
            results.append({
                "Symbol": symbol,
                "Volatile_Days_1pct": total_1pct_days,
                "ORB_Breaks": total_orb_breaks,
                "Reliability_Recall": round(reliability, 3),
                "Precision_Factor": round(precision, 3)
            })
        except Exception as e:
            print(f"  ❌ Error {symbol}: {e}")

    if results:
        final_df = pd.DataFrame(results).sort_values("Precision_Factor", ascending=False)
        final_df.to_csv(OUTPUT_FILE, index=False)
        print(f"\n✨ Clean Stats saved to: {OUTPUT_FILE}")

if __name__ == "__main__":
    calculate_precision()
