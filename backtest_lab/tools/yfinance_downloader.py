import yfinance as yf
import argparse
import os
import pandas as pd
from datetime import datetime, timedelta

def download_data(ticker, interval, start, end, output_dir):
    """
    Downloads data from yfinance and saves it to a CSV file.
    """
    print(f"🚀 Downloading {ticker} ({interval}) from {start} to {end}...")
    
    try:
        data = yf.download(ticker, interval=interval, start=start, end=end)
        
        if data.empty:
            print(f"⚠️ No data found for {ticker} with the given parameters.")
            return
        
        # Flatten MultiIndex columns if present (common in newer yfinance versions)
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)
            
        print(f"✅ Downloaded {len(data)} rows.")
        
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        # Construct filename
        filename = f"{ticker.replace('=', '_')}_{interval}_{start}_{end}.csv"
        filepath = os.path.join(output_dir, filename)
        
        data.to_csv(filepath)
        print(f"💾 Data saved to: {filepath}")
        
        # Print a snippet
        print("\n--- Data Snippet ---")
        print(data.head())
        print("--------------------")
        
    except Exception as e:
        print(f"❌ Error downloading data: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="yfinance Data Downloader Utility")
    parser.add_argument("--ticker", type=str, default="MNQ=F", help="Ticker symbol (e.g., MNQ=F, ^NSEI)")
    parser.add_argument("--interval", type=str, default="1m", help="Data interval (1m, 2m, 5m, 15m, 1h, 1d)")
    parser.add_argument("--start", type=str, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", type=str, help="End date (YYYY-MM-DD)")
    parser.add_argument("--days", type=int, help="Number of days back from today (if start/end not provided)")
    parser.add_argument("--output", type=str, default="python/backtest_lab/data/yfinance", help="Output directory")

    args = parser.parse_args()

    # Handle date logic
    if args.start and args.end:
        start_date = args.start
        end_date = args.end
    elif args.days:
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=args.days)).strftime("%Y-%m-%d")
    else:
        # Default to the user's requested range if nothing specified
        start_date = "2025-04-01"
        end_date = "2025-04-08"

    download_data(args.ticker, args.interval, start_date, end_date, args.output)
