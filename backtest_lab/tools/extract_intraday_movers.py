import pandas as pd
import json
import os
import argparse
from datetime import datetime

DATA_DIR = "backtest_lab/data/stocks/"
OUTPUT_DIR = "backtest_lab/data/intraday1pct/"

def process_stocks(batch_index, batch_size=10):
    # Ensure output dir exists
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Get all stock files
    all_files = sorted([f for f in os.listdir(DATA_DIR) if f.endswith("_minute.csv")])
    
    # Select batch
    start_idx = batch_index * batch_size
    end_idx = min(start_idx + batch_size, len(all_files))
    batch_files = all_files[start_idx:end_idx]
    
    if not batch_files:
        print(f"🏁 No more stocks to process for batch {batch_index}.")
        return

    print(f"🚀 Processing Batch {batch_index}: {batch_files}")

    for f in batch_files:
        symbol = f.replace("_minute.csv", "")
        file_path = os.path.join(DATA_DIR, f)
        
        try:
            df = pd.read_csv(file_path)
            # Ensure date column is datetime
            df['date'] = pd.to_datetime(df['date'])
            
            # Group by day
            df['day'] = df['date'].dt.date
            days = df.groupby('day')
            
            saved_count = 0
            for day, day_df in days:
                d_high = day_df['high'].max()
                d_low = day_df['low'].min()
                
                if d_low == 0: continue
                
                # Intra-day Range Calculation
                range_pct = (d_high - d_low) / d_low * 100
                
                if range_pct > 1.0:
                    # Meet criteria: Store 1min candles as JSON
                    output_filename = f"{symbol}_{day}.json"
                    output_path = os.path.join(OUTPUT_DIR, output_filename)
                    
                    # Convert to list of dicts for JSON
                    candles = day_df.drop(columns=['day']).to_dict(orient='records')
                    # Format dates back to string for JSON serialization
                    for c in candles:
                        c['date'] = c['date'].strftime('%Y-%m-%d %H:%M:%S')
                    
                    with open(output_path, 'w') as out_f:
                        json.dump(candles, out_f, indent=2)
                    saved_count += 1
            
            print(f"✅ {symbol}: Saved {saved_count} days with >1% intraday move.")
            
        except Exception as e:
            print(f"❌ Error processing {symbol}: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--batch', type=int, default=0, help="Index of the batch to process (0, 1, 2...)")
    parser.add_argument('--size', type=int, default=10, help="Number of stocks per batch")
    args = parser.parse_args()
    
    process_stocks(args.batch, args.size)
