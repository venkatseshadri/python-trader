import pandas as pd
import numpy as np
import os

REVAMP_FILE = "backtest_lab/orbiter_revamp_data.csv"
OUTPUT_FILE = "backtest_lab/data/gap_exhaustion_study.csv"

def analyze_gap_impact():
    if not os.path.exists(REVAMP_FILE):
        print(f"❌ Source file {REVAMP_FILE} not found.")
        return
    df = pd.read_csv(REVAMP_FILE)
    df['abs_gap'] = df['Gap%'].abs()
    df['abs_total_move'] = df['Total_Move%'].abs()
    print(f"🚀 Analyzing Gap Impact for {len(df)} mover events...")
    results = []
    symbols = df['Symbol'].unique()
    for symbol in symbols:
        df_sym = df[df['Symbol'] == symbol]
        if len(df_sym) < 10: continue
        gap_move_corr = df_sym['abs_gap'].corr(df_sym['abs_total_move'])
        gap_pb_corr = df_sym['abs_gap'].corr(df_sym['PB_Depth%'])
        results.append({
            "Symbol": symbol,
            "Avg_Gap_%": round(df_sym['abs_gap'].mean(), 3),
            "Avg_Intraday_Move_%": round(df_sym['abs_total_move'].mean(), 3),
            "Gap_vs_Move_Corr": round(gap_move_corr, 3),
            "Gap_vs_Pullback_Corr": round(gap_pb_corr, 3),
            "Events": len(df_sym)
        })
    if results:
        final_df = pd.DataFrame(results).sort_values("Gap_vs_Move_Corr")
        final_df.to_csv(OUTPUT_FILE, index=False)
        print(f"\n✨ Gap Exhaustion Study saved to: {OUTPUT_FILE}")
        avg_gap_corr = final_df['Gap_vs_Move_Corr'].mean()
        avg_pb_corr = final_df['Gap_vs_Pullback_Corr'].mean()
        print(f"\n🧠 GLOBAL HYPOTHESIS VALIDATION:")
        print(f"1. Gap size vs. Move magnitude correlation: {avg_gap_corr:.3f}")
        if avg_gap_corr < -0.2:
            print("   🟢 VALIDATED: Large gaps consistently lead to smaller intraday moves.")
        else:
            print("   🔴 WEAK: Gaps do not significantly 'exhaust' the intraday potential.")
        print(f"2. Gap size vs. Pullback depth correlation: {avg_pb_corr:.3f}")
        if avg_pb_corr > 0.2:
            print("   🟢 VALIDATED: Large gaps lead to deeper intraday reversals.")
        print("\n🏆 STOCKS WITH HIGHEST GAP EXHAUSTION (Strongest Negative Correlation):")
        print("-" * 90)
        print(final_df.head(15).to_string(index=False))

if __name__ == "__main__":
    analyze_gap_impact()
