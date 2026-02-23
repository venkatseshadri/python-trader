import pandas as pd
import glob
import os
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime

def analyze_correlations(data_dir, output_dir):
    """
    Performs correlation analysis on metal data.
    """
    print(f"🔍 Analyzing metal correlations in {data_dir}...")
    
    # Load all CSV files in the directory
    csv_files = glob.glob(os.path.join(data_dir, "*.csv"))
    
    if not csv_files:
        print("❌ No CSV files found in the directory.")
        return

    all_data = {}
    
    for file in csv_files:
        ticker = os.path.basename(file).split('_')[0]
        # Only take 1m data for intraday correlation
        if "_1m_" not in file:
            continue
            
        print(f"📊 Loading {ticker}...")
        df = pd.read_csv(file)
        
        # Newer pandas/yfinance MultiIndex cleanup
        if 'Price' in df.columns and 'Datetime' in df.columns:
            # Handle possible MultiIndex structure from CSV
            pass
            
        # Standardize Datetime
        if 'Datetime' in df.columns:
            df['Datetime'] = pd.to_datetime(df['Datetime'])
            df.set_index('Datetime', inplace=True)
        elif 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date'])
            df.set_index('Date', inplace=True)
            
        # Keep only Close price
        if 'Close' in df.columns:
            all_data[ticker] = df['Close']
        else:
            # Try to find Close in multi-level
            close_cols = [c for r in df.columns if 'Close' in r]
            if close_cols:
                all_data[ticker] = df[close_cols[0]]

    if not all_data:
        print("❌ No valid close price data found.")
        return

    # Combine into a single DataFrame
    combined_df = pd.DataFrame(all_data)
    
    # Forward fill missing values (common in different trading hours)
    combined_df.ffill(inplace=True)
    combined_df.dropna(inplace=True)
    
    if combined_df.empty:
        print("❌ Combined DataFrame is empty after alignment.")
        return

    print(f"✅ Aligned {len(combined_df)} rows of data.")

    # Calculate returns
    returns_df = combined_df.pct_change().dropna()
    
    # 1. Price Correlation (Levels)
    price_corr = combined_df.corr()
    
    # 2. Returns Correlation (Momentum)
    returns_corr = returns_df.corr()
    
    print("\n--- Returns Correlation Matrix ---")
    print(returns_corr)
    
    # Save Heatmap
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    plt.figure(figsize=(10, 8))
    sns.heatmap(returns_corr, annot=True, cmap='coolwarm', fmt=".2f")
    plt.title(f"Metal Returns Correlation (1m) - {timestamp}")
    heatmap_path = os.path.join(output_dir, f"metal_returns_corr_{timestamp}.png")
    plt.savefig(heatmap_path)
    print(f"🖼️ Heatmap saved to: {heatmap_path}")
    
    # Identify highest correlation pairs
    print("\n🔥 High Correlation Pairs (> 0.70):")
    for i in range(len(returns_corr.columns)):
        for j in range(i+1, len(returns_corr.columns)):
            if abs(returns_corr.iloc[i, j]) > 0.70:
                print(f"🔗 {returns_corr.columns[i]} <-> {returns_corr.columns[j]}: {returns_corr.iloc[i, j]:.2f}")

    # Advanced Lead-Lag Analysis (Cross-Correlation)
    print("\n⏳ Advanced Lead-Lag Matrix (Max Correlation at Lag):")
    lags = range(-10, 11)  # -10 to +10 minutes
    lead_lag_results = []
    
    for i in range(len(returns_df.columns)):
        for j in range(len(returns_df.columns)):
            if i == j: continue
            ticker_a = returns_df.columns[i]
            ticker_b = returns_df.columns[j]
            
            corrs = [returns_df.iloc[:, i].shift(lag).corr(returns_df.iloc[:, j]) for lag in lags]
            max_corr = max(corrs)
            best_lag = lags[corrs.index(max_corr)]
            
            if best_lag != 0 and max_corr > 0.30:  # Only report significant non-zero lag
                print(f"🕒 {ticker_a} leads {ticker_b} by {best_lag} min (Corr: {max_corr:.2f})")
                lead_lag_results.append({'lead': ticker_a, 'lag_target': ticker_b, 'lag_min': best_lag, 'corr': max_corr})

    # Spread Divergence (Gold vs Silver)
    if 'GC' in combined_df.columns and 'SI' in combined_df.columns:
        print("\n📈 Analyzing GC/SI Spread Divergence...")
        # Normalize to start of data for spread tracking
        norm_gc = combined_df['GC'] / combined_df['GC'].iloc[0]
        norm_si = combined_df['SI'] / combined_df['SI'].iloc[0]
        spread = norm_gc - norm_si
        
        # Calculate Z-Score of spread
        spread_z = (spread - spread.rolling(60).mean()) / spread.rolling(60).std()
        
        print(f"📉 Current GC/SI Spread Z-Score: {spread_z.iloc[-1]:.2f}")
        if abs(spread_z.iloc[-1]) > 2:
            direction = "GOLD OVERVALUED" if spread_z.iloc[-1] > 0 else "SILVER OVERVALUED"
            print(f"⚠️ SPREAD DIVERGENCE DETECTED: {direction} (Mean Reversion Likely)")

    # Volatility Ranking
    print("\n⚡ Current Intraday Volatility (1h Rolling Std Dev %):")
    volatility = returns_df.rolling(60).std() * (60**0.5) * 100 # Approx hourly vol
    latest_vol = volatility.iloc[-1].sort_values(ascending=False)
    for ticker, vol in latest_vol.items():
        print(f"🚩 {ticker}: {vol:.4f}% per hour")

if __name__ == "__main__":
    DATA_DIR = "python/backtest_lab/data/yfinance"
    OUTPUT_DIR = "python/backtest_lab/reports/correlation"
    analyze_correlations(DATA_DIR, OUTPUT_DIR)
