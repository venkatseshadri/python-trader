import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
from datetime import datetime

def analyze_ratio_arbitrage(ticker_a, ticker_b, data_dir, output_dir):
    """
    Analyzes Ratio Arbitrage (Pairs Trading) opportunities between two tickers.
    """
    print(f"📊 Analyzing Ratio: {ticker_a} / {ticker_b}...")
    
    # Load data
    file_a = [f for f in os.listdir(data_dir) if f.startswith(ticker_a) and "_1m_" in f]
    file_b = [f for f in os.listdir(data_dir) if f.startswith(ticker_b) and "_1m_" in f]
    
    if not file_a or not file_b:
        print("❌ Missing 1m data for one or both tickers.")
        return

    df_a = pd.read_csv(os.path.join(data_dir, file_a[0]))
    df_b = pd.read_csv(os.path.join(data_dir, file_b[0]))
    
    for df in [df_a, df_b]:
        df['Datetime'] = pd.to_datetime(df['Datetime'])
        df.set_index('Datetime', inplace=True)
        
    # Align data
    combined = pd.DataFrame({
        'A': df_a['Close'],
        'B': df_b['Close']
    }).ffill().dropna()
    
    # Calculate Ratio
    combined['ratio'] = combined['A'] / combined['B']
    
    # Calculate Mean and Z-Score of the ratio
    window = 120 # 2-hour rolling window for MCX
    combined['mean'] = combined['ratio'].rolling(window=window).mean()
    combined['std'] = combined['ratio'].rolling(window=window).std()
    combined['zscore'] = (combined['ratio'] - combined['mean']) / combined['std']
    
    # Identify entry points (Z-Score > 2 or < -2)
    combined['buy_signal'] = (combined['zscore'] < -2).astype(int)
    combined['sell_signal'] = (combined['zscore'] > 2).astype(int)
    
    # Simulate basic PnL (Buy A Sell B when Z < -2, Sell A Buy B when Z > 2)
    # This is a simplification
    
    print(f"✅ Aligned {len(combined)} minutes of data.")
    print(f"📈 Average Ratio: {combined['ratio'].mean():.4f}")
    print(f"🔥 Signals Detected: Buy {ticker_a}/{ticker_b}: {combined['buy_signal'].sum()}, Sell {ticker_a}/{ticker_b}: {combined['sell_signal'].sum()}")

    # Plot results
    os.makedirs(output_dir, exist_ok=True)
    plt.figure(figsize=(12, 10))
    
    plt.subplot(2, 1, 1)
    plt.plot(combined['ratio'], label='Ratio', color='blue')
    plt.plot(combined['mean'], label='Rolling Mean', color='orange', linestyle='--')
    plt.title(f"{ticker_a} / {ticker_b} Ratio")
    plt.legend()
    
    plt.subplot(2, 1, 2)
    plt.plot(combined['zscore'], label='Z-Score', color='purple')
    plt.axhline(2, color='red', linestyle='--')
    plt.axhline(-2, color='green', linestyle='--')
    plt.axhline(0, color='black', alpha=0.3)
    plt.title("Ratio Z-Score")
    plt.legend()
    
    plt.tight_layout()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    plot_path = os.path.join(output_dir, f"ratio_arb_{ticker_a}_{ticker_b}_{timestamp}.png")
    plt.savefig(plot_path)
    print(f"🖼️ Ratio analysis plot saved to: {plot_path}")

if __name__ == "__main__":
    DATA_DIR = "python/backtest_lab/data/yfinance"
    OUTPUT_DIR = "python/backtest_lab/reports/ratio"
    
    # Gold vs Silver (Classic Pair)
    analyze_ratio_arbitrage("GC", "SI", DATA_DIR, OUTPUT_DIR)
    
    # Copper vs Aluminum (Industrial Metal Correlation)
    analyze_ratio_arbitrage("HG", "ALI", DATA_DIR, OUTPUT_DIR)
