import pandas as pd
import numpy as np
import talib
import os
import sys

def analyze_momentum(csv_path):
    if not os.path.exists(csv_path):
        print(f"❌ Error: {csv_path} not found.")
        return

    df = pd.read_csv(csv_path, header=None, names=['date', 'open', 'high', 'low', 'close', 'vol'])
    closes = df['close'].values

    talib.set_compatibility(1)
    ema5 = talib.EMA(closes, timeperiod=5)
    ema9 = talib.EMA(closes, timeperiod=9)
    talib.set_compatibility(0)

    df['ema5'] = ema5
    df['ema9'] = ema9
    df['gap'] = df['ema5'] - df['ema9']
    
    # Calculate Slopes (5-min window)
    df['ema5_slope'] = (df['ema5'] - df['ema5'].shift(5)) / df['close'] * 100
    df['gap_expansion'] = (df['gap'] - df['gap'].shift(5)) / df['close'] * 100

    print("\n--- Technical Momentum Analysis (Last 20 Candles) ---")
    print(df[['date', 'close', 'ema5_slope', 'gap_expansion']].tail(20))

if __name__ == "__main__":
    default_csv = 'python-trader/orbiter/tests/data/nifty_ta_chunk.csv'
    path = sys.argv[1] if len(sys.argv) > 1 else default_csv
    analyze_momentum(path)
