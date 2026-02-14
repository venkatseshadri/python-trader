import pandas as pd
import os
from datetime import datetime

class DataLoader:
    def __init__(self, csv_path):
        self.csv_path = csv_path
        self.columns = ['date', 'open', 'high', 'low', 'close', 'volume']

    def load_data(self, days=250):
        """
        Loads the most recent portion of the NIFTY 50 archive.
        Control row count based on requested days.
        """
        if not os.path.exists(self.csv_path):
            raise FileNotFoundError(f"Data file not found: {self.csv_path}")

        # Estimate rows: 375 trading mins per day. 
        # 3000 days * 375 = ~1.1 million rows for a full 10-year run.
        rows_to_load = days * 400 
        
        print(f"⏳ Fast-loading last {days} days (~{rows_to_load} candles)...")
        
        total_rows = sum(1 for _ in open(self.csv_path))
        skip_count = max(1, total_rows - rows_to_load)

        df = pd.read_csv(self.csv_path, names=self.columns, header=0, skiprows=skip_count)
        
        df['date'] = pd.to_datetime(df['date'])
        df.sort_values('date', inplace=True)
        df.reset_index(drop=True, inplace=True)
        
        print(f"✅ Loaded {len(df)} candles from {df['date'].min()} to {df['date'].max()}")
        return df

    def get_intraday_data(self, df, date_str):
        """Extracts a specific day's data for row-by-row simulation."""
        target_date = pd.to_datetime(date_str).date()
        return df[df['date'].dt.date == target_date].copy()
