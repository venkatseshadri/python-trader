import pandas as pd
import json
import os
from datetime import time as dt_time

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

def generate_summaries():
    # Only process symbols that have subfolders already (from the previous batch)
    symbols = [d for d in os.listdir(OUTPUT_DIR) if os.path.isdir(os.path.join(OUTPUT_DIR, d))]
    
    if not symbols:
        print("⚠️ No symbol folders found in intraday1pct.")
        return

    print(f"🚀 Generating Summaries for: {symbols}")

    for symbol in symbols:
        csv_path = os.path.join(DATA_DIR, f"{symbol}_minute.csv")
        if not os.path.exists(csv_path): 
            print(f"⚠️ Source CSV missing for {symbol}")
            continue
        
        try:
            df = pd.read_csv(csv_path)
            df['date'] = pd.to_datetime(df['date'])
            df = df.set_index('date')
            
            # Aggregate to daily to find movers and yesterday's close
            daily = df.resample('1D').agg({'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last'}).dropna()
            daily['prev_close'] = daily['close'].shift(1)
            
            # Find days matching the >1% range criteria
            valid_days = daily[(daily['high'] - daily['low']) / daily['low'] > 0.01].index
            
            stock_summaries = []
            for day_ts in valid_days:
                day_data = df[df.index.date == day_ts.date()]
                d_stats = daily.loc[day_ts]
                
                summary = {
                    "date": day_ts.strftime('%Y-%m-%d'),
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
            
            output_path = os.path.join(OUTPUT_DIR, f"{symbol}_Summ.json")
            with open(output_path, 'w') as f:
                json.dump(stock_summaries, f, indent=2)
            print(f"✅ {symbol}: Generated summary with {len(stock_summaries)} events.")
            
        except Exception as e:
            print(f"❌ Error summarizing {symbol}: {e}")

if __name__ == "__main__":
    generate_summaries()
