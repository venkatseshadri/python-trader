import pandas as pd
import numpy as np

def discover_patterns(csv_path):
    df = pd.read_csv(csv_path)
    print(f"🔍 Analyzing {len(df)} 1% Mover events for patterns...")

    def identify_filters(row):
        filters = []
        direction = row['Direction']
        if row['Trend_Aligned']: filters.append("STRUCT_ALIGN")
        if direction == 'LONG' and row['LTP_gt_YHigh']: filters.append("YHIGH_BREAK")
        if direction == 'SHORT' and row['LTP_lt_YLow']: filters.append("YLOW_BREAK")
        if direction == 'SHORT' and row['Yesterday_Color'] == 'Green' and row['High_gt_YLow'] and row['LTP_lt_YLow']:
            filters.append("BEAR_FLIP")
        if direction == 'LONG' and row['Yesterday_Color'] == 'Red' and row['Low_lt_YHigh'] and row['LTP_gt_YHigh']:
            filters.append("BULL_FLIP")
        if row['EMA5_gt_9_Always']: filters.append("CLEAN_MOM")
        if not row['ADX_Exhaustion']: filters.append("STRONG_ADX")
        if row['Ribbon_Compressed']: filters.append("VOL_EXP_READY")
        if abs(row['Gap%']) > 0.5: filters.append("GAP_PLAY")
        return "|".join(sorted(filters)) if filters else "NO_FILTER_MATCH"

    df['Pattern'] = df.apply(identify_filters, axis=1)
    
    patterns = df.groupby('Pattern').agg({
        'Total_Move%': ['count', 'mean'],
        'PB_Depth%': 'mean'
    })
    
    patterns.columns = ['Count', 'Avg_Move%', 'Avg_Pullback%']
    patterns['Reliability'] = (abs(patterns['Avg_Move%']) / (patterns['Avg_Pullback%'] + 1)) * (patterns['Count'] / len(df))
    patterns = patterns.sort_values('Count', ascending=False)
    
    print("\n🏆 TOP 5 PATTERN COMBINATIONS BY FREQUENCY:")
    print("-" * 110)
    print(patterns.head(5).to_string())
    
    print("\n🎯 TOP 3 BY RELIABILITY (Move vs Risk vs Frequency):")
    print("-" * 110)
    print(patterns.sort_values('Reliability', ascending=False).head(3).to_string())

if __name__ == "__main__":
    discover_patterns("backtest_lab/orbiter_revamp_data.csv")
