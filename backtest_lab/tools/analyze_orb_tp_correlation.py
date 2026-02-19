import pandas as pd
import json
import os
import numpy as np

SUBSET_DIR = "backtest_lab/data/intraday1pct/"
STATS_FILE = "backtest_lab/data/nifty_volatility_stats.csv"
OUTPUT_FILE = "backtest_lab/data/orb_tp_correlation_results.csv"

def analyze_correlation():
    df_stats = pd.read_csv(STATS_FILE)
    elite_symbols = df_stats[df_stats['Volatility_Frequency_%'] >= 95.0]['Symbol'].tolist()
    elite_symbols = [s for s in elite_symbols if s != 'ENRIN' and 'NIFTY' not in s]
    results = []
    print(f"🚀 Analyzing ORB-TP Correlation for {len(elite_symbols)} Elite stocks...")

    for symbol in elite_symbols:
        symbol_dir = os.path.join(SUBSET_DIR, symbol)
        if not os.path.exists(symbol_dir): continue
        json_files = [f for f in os.listdir(symbol_dir) if f.endswith(".json") and "_" in f]
        day_data = []
        for f_name in json_files:
            try:
                with open(os.path.join(symbol_dir, f_name), 'r') as f:
                    candles = json.load(f)
                if len(candles) < 30: continue
                df = pd.DataFrame(candles)
                day_h, day_l = df['high'].max(), df['low'].min()
                total_range_pct = (day_h - day_l) / day_l * 100
                orb_h, orb_l = df.iloc[:15]['high'].max(), df.iloc[:15]['low'].min()
                orb_size_pct = (orb_h - orb_l) / orb_l * 100
                post_orb = df.iloc[15:]
                broken_h = post_orb[post_orb['high'] > orb_h]
                broken_l = post_orb[post_orb['low'] < orb_l]
                if not broken_h.empty or not broken_l.empty:
                    idx_h = broken_h.index[0] if not broken_h.empty else 9999
                    idx_l = broken_l.index[0] if not broken_l.empty else 9999
                    if idx_h < idx_l:
                        max_p = post_orb.loc[idx_h:]['high'].max()
                        post_break_move = (max_p - orb_h) / orb_h * 100
                    else:
                        min_p = post_orb.loc[idx_l:]['low'].min()
                        post_break_move = (orb_l - min_p) / orb_l * 100
                    day_data.append({"orb": orb_size_pct, "pb": post_break_move, "range": total_range_pct})
            except: pass

        if day_data:
            df_sym = pd.DataFrame(day_data)
            correlation = df_sym['orb'].corr(df_sym['pb'])
            results.append({
                "Symbol": symbol,
                "Avg_Total_Range_%": round(df_sym['range'].mean(), 2),
                "Avg_ORB_%": round(df_sym['orb'].mean(), 2),
                "Avg_Post_Break_%": round(df_sym['pb'].mean(), 2),
                "Avg_Combined_Budget_%": round((df_sym['orb'] + df_sym['pb']).mean(), 2),
                "Correlation": round(correlation, 3),
                "Days": len(df_sym)
            })
            print(f"✅ {symbol}: Budget={results[-1]['Avg_Combined_Budget_%']}% | Corr={correlation:.3f}")

    if results:
        final_df = pd.DataFrame(results).sort_values("Avg_Combined_Budget_%", ascending=False)
        final_df.to_csv(OUTPUT_FILE, index=False)
        print(f"\n✨ Analysis saved to: {OUTPUT_FILE}")
        overall_corr = final_df['Correlation'].mean()
        print(f"\n🧠 HYPOTHESIS VALIDATION: Avg Correlation = {overall_corr:.3f}")
        if overall_corr < -0.3:
            print("🟢 VALIDATED: Strong negative correlation. Large ORB = Small TP potential.")
        else:
            print("🔴 WEAK: ORB size doesn't strongly predict the remaining move.")

if __name__ == "__main__":
    analyze_correlation()
