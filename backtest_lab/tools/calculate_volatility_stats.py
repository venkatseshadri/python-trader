import pandas as pd
import os

SUBSET_DIR = "backtest_lab/data/intraday1pct/"
SOURCE_DIR = "backtest_lab/data/stocks/"
OUTPUT_FILE = "backtest_lab/data/nifty_volatility_stats.csv"

def calculate_stats():
    symbols = sorted([d for d in os.listdir(SUBSET_DIR) if os.path.isdir(os.path.join(SUBSET_DIR, d))])
    results = []
    print(f"🚀 Calculating Volatility Stats for {len(symbols)} symbols from existing subset...")

    for symbol in symbols:
        symbol_dir = os.path.join(SUBSET_DIR, symbol)
        source_csv = os.path.join(SOURCE_DIR, f"{symbol}_minute.csv")
        if not os.path.exists(source_csv): continue
        try:
            volatile_count = len([f for f in os.listdir(symbol_dir) if f.endswith(".json") and "_" in f])
            df_dates = pd.read_csv(source_csv, usecols=['date'])
            total_days = pd.to_datetime(df_dates['date']).dt.date.nunique()
            freq_pct = (volatile_count / total_days * 100) if total_days > 0 else 0
            results.append({
                "Symbol": symbol,
                "Total_Traded_Days": total_days,
                "Volatile_Days_1pct": volatile_count,
                "Volatility_Frequency_%": round(freq_pct, 2)
            })
            print(f"✅ {symbol}: {volatile_count}/{total_days} days ({freq_pct:.1f}%)")
        except Exception as e:
            print(f"❌ Error {symbol}: {e}")

    if results:
        final_df = pd.DataFrame(results).sort_values("Volatility_Frequency_%", ascending=False)
        final_df.to_csv(OUTPUT_FILE, index=False)
        print(f"\n✨ Final Stats saved to: {OUTPUT_FILE}")
        print("\n🏆 TOP 10 CONSISTENT MOVERS:")
        print("-" * 60)
        print(final_df.head(10).to_string(index=False))

if __name__ == "__main__":
    calculate_stats()
