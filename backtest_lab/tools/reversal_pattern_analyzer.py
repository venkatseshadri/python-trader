import pandas as pd
import numpy as np
import talib
import os
import glob
from python.orbiter.utils.utils import safe_float

def analyze_metal_reversals(file_path):
    ticker = os.path.basename(file_path).split('_')[0]
    df_1m = pd.read_csv(file_path)
    
    # Standardize Datetime column name
    if 'Datetime' not in df_1m.columns and 'Date' in df_1m.columns:
        df_1m.rename(columns={'Date': 'Datetime'}, inplace=True)
        
    df_1m['Datetime'] = pd.to_datetime(df_1m['Datetime'])
    df_1m.set_index('Datetime', inplace=True)
    
    # Resample for 5m and 15m views
    df_5m = df_1m.resample('5min').agg({'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'}).dropna()
    df_15m = df_1m.resample('15min').agg({'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'}).dropna()

    print(f"\n🔍 Analyzing Reversal Patterns for {ticker}...")

    # 1. Calculate Indicators for each TF
    # 15m Indicators
    df_15m['ATR'] = talib.ATR(df_15m['High'], df_15m['Low'], df_15m['Close'], timeperiod=14)
    df_15m['ATR_Mean'] = df_15m['ATR'].rolling(20).mean()
    df_15m['ADX'] = talib.ADX(df_15m['High'], df_15m['Low'], df_15m['Close'], timeperiod=14)
    
    # 5m Indicators
    df_5m['EMA5'] = talib.EMA(df_5m['Close'], timeperiod=5)
    df_5m['Scope'] = (df_5m['EMA5'] - df_5m['EMA5'].shift(1)) / df_5m['Close'] * 100
    
    # 1m Indicators
    df_1m['EMA5'] = talib.EMA(df_1m['Close'], timeperiod=5)
    df_1m['EMA9'] = talib.EMA(df_1m['Close'], timeperiod=9)
    df_1m['Gap'] = df_1m['EMA5'] - df_1m['EMA9']

    # 2. Find "Exhaustion" Points (Price Peaks/Troughs)
    # Reduce window to find more local turns
    peaks = df_1m[(df_1m['Close'] == df_1m['Close'].rolling(30, center=True).max())].copy()
    troughs = df_1m[(df_1m['Close'] == df_1m['Close'].rolling(30, center=True).min())].copy()
    
    reversal_stats = []

    for timestamp in list(peaks.index) + list(troughs.index):
        is_peak = timestamp in peaks.index
        try:
            # Get corresponding TF rows
            row_1m = df_1m.loc[timestamp]
            row_5m = df_5m.asof(timestamp)
            row_15m = df_15m.asof(timestamp)
            
            # Pattern 1: 15m Exhaustion (ATR > 1.2x Mean)
            is_exhausted = row_15m['ATR'] > (row_15m['ATR_Mean'] * 1.2)
            
            # Pattern 2: 5m Stalling (Scope drops near 0)
            is_stalling = abs(row_5m['Scope']) < 0.05
            
            # Pattern 3: 1m Divergence (Gap shrinking vs prev 2 mins)
            gap_now = abs(row_1m['Gap'])
            gap_prev = abs(df_1m.shift(2).loc[timestamp]['Gap'])
            is_divergent = gap_now < gap_prev
            
            score = (0.3 if is_exhausted else 0) + (0.3 if is_stalling else 0) + (0.4 if is_divergent else 0)
            
            if score >= 0.6:
                # Check if it actually reversed (Price 10 mins later)
                future_idx = df_1m.index.get_loc(timestamp) + 10
                if future_idx < len(df_1m):
                    price_later = df_1m['Close'].iloc[future_idx]
                    if is_peak:
                        actual_reversal = price_later < row_1m['Close']
                    else:
                        actual_reversal = price_later > row_1m['Close']
                        
                    reversal_stats.append({
                        'time': timestamp,
                        'type': 'PEAK' if is_peak else 'TROUGH',
                        'score': score,
                        'success': actual_reversal,
                        '15m_adx': row_15m['ADX'],
                        '5m_scope': row_5m['Scope']
                    })
        except:
            continue

    if reversal_stats:
        stats_df = pd.DataFrame(reversal_stats)
        win_rate = stats_df['success'].mean() * 100
        print(f"✅ Found {len(stats_df)} Reversal Signals. Prediction Accuracy: {win_rate:.1f}%")
        print(f"📈 Avg ADX at Reversal: {stats_df['15m_adx'].mean():.1f}")
    else:
        print("⚠️ No strong reversal patterns detected in this sample.")

if __name__ == "__main__":
    DATA_DIR = "python/backtest_lab/data/yfinance"
    # Process all available 1m CSV files
    files = glob.glob(os.path.join(DATA_DIR, "*_1m_*.csv"))
    for f in files:
        analyze_metal_reversals(f)
