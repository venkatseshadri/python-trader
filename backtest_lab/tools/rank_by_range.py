import pandas as pd
import os

def rank_stocks():
    subset_dir = "backtest_lab/data/intraday1pct/"
    symbols = sorted([d for d in os.listdir(subset_dir) if os.path.isdir(os.path.join(subset_dir, d))])
    avg_ranges = []
    for s in symbols:
        if s == 'ENRIN': continue
        csv_path = os.path.join(subset_dir, s, f"{s}.csv")
        if os.path.exists(csv_path):
            df = pd.read_csv(csv_path)
            avg_ranges.append({
                'Symbol': s,
                'Avg_Intraday_Range_%': df['PCT_MOVE'].mean(),
                'Max_Ever_Range_%': df['PCT_MOVE'].max()
            })
    final = pd.DataFrame(avg_ranges).sort_values('Avg_Intraday_Range_%', ascending=False)
    print("\n🏆 STOCKS WITH HIGHEST AVERAGE INTRADAY VOLATILITY:")
    print("-" * 65)
    print(final.head(15).round(2).to_string(index=False))

if __name__ == "__main__":
    rank_stocks()
