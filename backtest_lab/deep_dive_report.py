import pandas as pd
import numpy as np

def deep_dive_report(file_path):
    df = pd.read_csv(file_path)
    df['Abs_Move%'] = df['Total_Move%'].abs()
    
    print("\n🔍 ORBITER DEEP-DIVE ARCHITECTURAL REPORT")
    print("="*60)

    # 1. THE "WICK" SIGNATURE
    avg_wick_overall = df['Day_Wick_U'].mean()
    avg_wick_exhaustion = df[df['ADX_Exhaustion'] == True]['Day_Wick_U'].mean()
    print(f"1. WICK BEHAVIOR:")
    print(f"   - Average Upper Wick: {avg_wick_overall:.3f}")
    print(f"   - Upper Wick during Exhaustion: {avg_wick_exhaustion:.3f}")
    print(f"   - INSIGHT: Exhaustion candles have {((avg_wick_exhaustion/avg_wick_overall)-1)*100:.1f}% larger upper wicks.")

    # 2. PULLBACK vs. REVERSAL
    avg_pb_depth = df[df['Pullback_Happened'] == True]['Pullback_Depth%'].mean()
    rev_rate = df['Reversal_Confirmed'].mean() * 100
    print(f"\n2. PULLBACK DYNAMICS:")
    print(f"   - Average Pullback Depth in 1% movers: {avg_pb_depth:.2f}%")
    print(f"   - Reversal Confirmation Rate: {rev_rate:.1f}%")
    print(f"   - INSIGHT: Only {rev_rate:.1f}% of moves recover after a pullback. Most 1% moves are 'one-way'.")

    # 3. EXHAUSTION TRIGGERS
    compression_mask = df['PrePeak_Compression'] == True
    exhaustion_with_compression = df[compression_mask]['ADX_Exhaustion'].mean() * 100
    print(f"\n3. EXHAUSTION SIGNALS:")
    print(f"   - ADX Exhaustion when Candle Compression occurs: {exhaustion_with_compression:.1f}%")
    print(f"   - INSIGHT: Candle compression is a {exhaustion_with_compression:.1f}% reliable lead indicator.")

    # 4. THE "GOLDEN HOUR" VS "DEAD ZONE"
    timing_stats = df.groupby('Best_Bucket').agg({
        'Abs_Move%': 'mean',
        'ADX_Exhaustion': 'mean',
        'Symbol': 'count'
    }).rename(columns={'Symbol': 'Event_Count', 'ADX_Exhaustion': 'Exhaustion_Prob'})
    
    print(f"\n4. TIMING ANALYSIS (BUCKETS):")
    print(timing_stats.to_string())
    print(f"   - INSIGHT: Bucket 1 (9:15-10:30) captures {timing_stats.loc[1, 'Event_Count']/len(df)*100:.1f}% of all major moves.")

    # 5. REVERSAL CONTEXT
    avg_pre_rev_adx = df[df['Pullback_Happened'] == True]['PreRev_ADX'].mean()
    print(f"\n5. PRE-REVERSAL STATE:")
    print(f"   - Average ADX before pullback starts: {avg_pre_rev_adx:.2f}")

    print("\n" + "="*60)
    print("🏁 FINAL FILTER ARCHITECTURE")
    print("="*60)
    print("RESTRICTIVE: Trend_Aligned == True AND Open_gt_YClose == True")
    print("SCORING:     B1_Move (High Weight) + Gap% (Med Weight)")
    print("EXIT/BLOCK:  Upper_Wick > 0.15 (Block) OR ATR_Compression == True (Exit)")
    print("="*60)

if __name__ == "__main__":
    deep_dive_report('backtest_lab/orbiter_revamp_data.csv')
