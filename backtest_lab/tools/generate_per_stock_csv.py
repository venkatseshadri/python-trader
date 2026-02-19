import pandas as pd
import json
import os
import argparse

OUTPUT_DIR = "backtest_lab/data/intraday1pct/"

def generate_csv_for_stock(symbol_dir, symbol):
    rows = []
    json_files = sorted([f for f in os.listdir(symbol_dir) if f.endswith(".json") and not f.endswith("_Summ.json") and f != f"{symbol}.json"])
    
    if not json_files:
        return

    for f_name in json_files:
        file_path = os.path.join(symbol_dir, f_name)
        try:
            with open(file_path, 'r') as f:
                candles = json.load(f)
            
            if not candles: continue
            
            df = pd.DataFrame(candles)
            d_open = df.iloc[0]['open']
            d_high = df['high'].max()
            d_low = df['low'].min()
            d_close = df.iloc[-1]['close']
            pct_move = (d_high - d_low) / d_low * 100
            
            # Extract date from filename (Symbol_YYYY-MM-DD.json)
            date_str = f_name.replace(f"{symbol}_", "").replace(".json", "")
            
            rows.append({
                "fileName": f_name,
                "date": date_str,
                "DAY_OPEN": round(float(d_open), 2),
                "DAY_HIGH": round(float(d_high), 2),
                "DAY_LOW": round(float(d_low), 2),
                "DAY_CLOSE": round(float(d_close), 2),
                "PCT_MOVE": round(float(pct_move), 2)
            })
        except Exception as e:
            print(f"  ❌ Error in {f_name}: {e}")

    if rows:
        output_csv = os.path.join(symbol_dir, f"{symbol}.csv")
        pd.DataFrame(rows).to_csv(output_csv, index=False)
        print(f"✅ {symbol}: Generated index CSV with {len(rows)} rows.")

def process_batch(batch_index, batch_size=10):
    all_symbols = sorted([d for d in os.listdir(OUTPUT_DIR) if os.path.isdir(os.path.join(OUTPUT_DIR, d))])
    
    start_idx = batch_index * batch_size
    end_idx = min(start_idx + batch_size, len(all_symbols))
    batch_symbols = all_symbols[start_idx:end_idx]
    
    if not batch_symbols:
        print(f"🏁 No more folders to process for batch {batch_index}.")
        return

    print(f"🚀 Processing Batch {batch_index}: {batch_symbols}")
    for symbol in batch_symbols:
        symbol_dir = os.path.join(OUTPUT_DIR, symbol)
        generate_csv_for_stock(symbol_dir, symbol)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--batch', type=int, required=True, help="Batch index (0, 1, 2...)")
    parser.add_argument('--size', type=int, default=10, help="Folders per batch")
    args = parser.parse_args()
    
    process_batch(args.batch, args.size)
