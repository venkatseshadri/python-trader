import pandas as pd
import os
import argparse

DATA_DIR = "backtest_lab/data/stocks/"
TEMP_DIR = "backtest_lab/data/temp_vol/"

def process_batch(batch_index, batch_size=10):
    os.makedirs(TEMP_DIR, exist_ok=True)
    
    all_files = sorted([f for f in os.listdir(DATA_DIR) if f.endswith("_minute.csv")])
    start_idx = batch_index * batch_size
    end_idx = min(start_idx + batch_size, len(all_files))
    batch_files = all_files[start_idx:end_idx]
    
    if not batch_files:
        print(f"🏁 Batch {batch_index} is empty. No more stocks.")
        return

    results = []
    print(f"🚀 Processing Batch {batch_index} ({start_idx+1} to {end_idx} of {len(all_files)})...")

    for i, f in enumerate(batch_files):
        symbol = f.replace("_minute.csv", "")
        file_path = os.path.join(DATA_DIR, f)
        
        try:
            df = pd.read_csv(file_path)
            df['date'] = pd.to_datetime(df['date'])
            
            # Group by date to get daily extremes
            daily = df.groupby(df['date'].dt.date).agg({'high': 'max', 'low': 'min'})
            
            total_days = len(daily)
            # Volatile if (High - Low) > 1% of Low
            volatile_days = daily[(daily['high'] - daily['low']) / daily['low'] * 100 > 1.0]
            volatile_count = len(volatile_days)
            
            freq_pct = (volatile_count / total_days * 100) if total_days > 0 else 0
            
            results.append({
                "Symbol": symbol,
                "Total_Days": total_days,
                "Volatile_Days": volatile_count,
                "Volatility_Frequency_%": round(freq_pct, 2)
            })
            
            print(f"  [{start_idx + i + 1}/{len(all_files)}] ✅ {symbol}: {freq_pct:.1f}%")
            
        except Exception as e:
            print(f"  ❌ Error {symbol}: {e}")

    if results:
        batch_df = pd.DataFrame(results)
        batch_file = os.path.join(TEMP_DIR, f"vol_batch_{batch_index}.csv")
        batch_df.to_csv(batch_file, index=False)
        print(f"💾 Batch results saved to {batch_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--batch', type=int, required=True)
    parser.add_argument('--size', type=int, default=10)
    args = parser.parse_args()
    
    process_batch(args.batch, args.size)
