import pandas as pd
import os

DATA_DIR = "backtest_lab/data/stocks/"
OUTPUT_FILE = "backtest_lab/data/nifty_volatility_frequency.csv"

def analyze_volatility():
    all_files = sorted([f for f in os.listdir(DATA_DIR) if f.endswith("_minute.csv")])
    results = []
    print(f"🚀 Analyzing Volatility Frequency for {len(all_files)} stocks...")

    for f in all_files:
        symbol = f.replace("_minute.csv", "")
        file_path = os.path.join(DATA_DIR, f)
        try:
            df = pd.read_csv(file_path)
            df['date'] = pd.to_datetime(df['date'])
            daily = df.groupby(df['date'].dt.date).agg({'high': 'max', 'low': 'min'})
            total_days = len(daily)
            volatile_days = daily[(daily['high'] - daily['low']) / daily['low'] * 100 > 1.0]
            volatile_count = len(volatile_days)
            freq_pct = (volatile_count / total_days * 100) if total_days > 0 else 0
            results.append({
                "Symbol": symbol,
                "Total_Days": total_days,
                "Volatile_Days": volatile_count,
                "Volatility_Frequency_%": round(freq_pct, 2)
            })
        except Exception as e:
            print(f"❌ Error processing {symbol}: {e}")

    if results:
        final_df = pd.DataFrame(results).sort_values("Volatility_Frequency_%", ascending=False)
        final_df.to_csv(OUTPUT_FILE, index=False)
        print(f"\n✅ Volatility Analysis complete! Saved to: {OUTPUT_FILE}")
        print("\n🏆 TOP 10 MOST VOLATILE STOCKS:")
        print("-" * 60)
        print(final_df.head(10).to_string(index=False))

if __name__ == "__main__":
    analyze_volatility()
