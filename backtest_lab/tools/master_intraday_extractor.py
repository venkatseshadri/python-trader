import pandas as pd
import json
import os
import argparse
from datetime import datetime, time as dt_time

DATA_DIR = "backtest_lab/data/stocks/"
OUTPUT_DIR = "backtest_lab/data/intraday1pct/"

def get_bucket_ohlc(df, start_t, end_t):
    mask = (df.index.time >= start_t) & (df.index.time < end_t)
    if not mask.any():
        return None
    sub = df[mask]
    return {
        "open": round(float(sub.iloc[0]['open']), 2),
        "high": round(float(sub['high'].max()), 2),
        "low": round(float(sub['low'].min()), 2),
        "close": round(float(sub.iloc[-1]['close']), 2)
    }

def process_all_remaining(start_batch=1, batch_size=10):
    # Ensure output dir exists
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Get all stock files
    all_files = sorted([f for f in os.listdir(DATA_DIR) if f.endswith("_minute.csv")])
    
    # Select files from start_batch onwards
    start_idx = start_batch * batch_size
    remaining_files = all_files[start_idx:]
    
    if not remaining_files:
        print("🏁 All stocks have already been processed.")
        return

    print(f"🚀 Master Extraction: Processing {len(remaining_files)} remaining stocks...")

    for f in remaining_files:
        symbol = f.replace("_minute.csv", "")
        file_path = os.path.join(DATA_DIR, f)
        symbol_dir = os.path.join(OUTPUT_DIR, symbol)
        os.makedirs(symbol_dir, exist_ok=True)
        
        try:
            df = pd.read_csv(file_path)
            df['date'] = pd.to_datetime(df['date'])
            
            # Helper for daily stats
            df_indexed = df.set_index('date')
            daily = df_indexed.resample('1D').agg({
                'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last'
            }).dropna()
            daily['prev_close'] = daily['close'].shift(1)
            
            stock_summaries = []
            saved_candles = 0
            
            # Find mover days
            valid_days = daily[(daily['high'] - daily['low']) / daily['low'] > 0.01].index
            
            for day_ts in valid_days:
                day_str = day_ts.strftime('%Y-%m-%d')
                day_data = df_indexed[df_indexed.index.date == day_ts.date()]
                d_stats = daily.loc[day_ts]
                
                # 1. Save Candle JSON inside symbol folder
                candle_output_path = os.path.join(symbol_dir, f"{symbol}_{day_str}.json")
                # Reset index to export date as column
                candles_list = day_data.reset_index().to_dict(orient='records')
                for c in candles_list:
                    c['date'] = c['date'].strftime('%Y-%m-%d %H:%M:%S')
                
                with open(candle_output_path, 'w') as out_f:
                    json.dump(candles_list, out_f, indent=2)
                saved_candles += 1
                
                # 2. Build Summary Entry
                summary = {
                    "date": day_str,
                    "intraday_high": round(float(d_stats['high']), 2),
                    "intraday_low": round(float(d_stats['low']), 2),
                    "yesterday_close": round(float(d_stats['prev_close']), 2) if not pd.isna(d_stats['prev_close']) else 0,
                    "open": round(float(d_stats['open']), 2),
                    "close": round(float(d_stats['close']), 2),
                    "B1": get_bucket_ohlc(day_data, dt_time(9,15), dt_time(10,30)),
                    "B2": get_bucket_ohlc(day_data, dt_time(10,30), dt_time(12,0)),
                    "B3": get_bucket_ohlc(day_data, dt_time(12,0), dt_time(13,30)),
                    "B4": get_bucket_ohlc(day_data, dt_time(13,30), dt_time(15,30))
                }
                stock_summaries.append(summary)
            
            # 3. Save Summary JSON in parent folder
            summary_output_path = os.path.join(OUTPUT_DIR, f"{symbol}_Summ.json")
            with open(summary_output_path, 'w') as f_summ:
                json.dump(stock_summaries, f_summ, indent=2)
                
            print(f"✅ {symbol}: Extracted {saved_candles} sessions and generated summary.")
            
        except Exception as e:
            print(f"❌ Error processing {symbol}: {e}")

if __name__ == "__main__":
    process_all_remaining(start_batch=1, batch_size=10)
