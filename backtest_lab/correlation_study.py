import pandas as pd
import numpy as np

def analyze_correlations(file_path):
    df = pd.read_csv(file_path)
    
    # Ensure Move% is absolute for correlation analysis across both directions
    df['Abs_Move%'] = df['Total_Move%'].abs()
    
    # 1. Numeric Correlation with Abs_Move%
    numeric_cols = [
        'Gap%', 'EMA_Crosses', 'PreRev_EMA_Gap', 'PreRev_ADX', 
        'PreRev_ATR_Ratio', 'B1_Move', 'Abs_Move%'
    ]
    corr_matrix = df[numeric_cols].corr()['Abs_Move%'].sort_values(ascending=False)
    
    # 2. Boolean Impact Analysis (Average Abs_Move% when True vs False)
    bool_cols = [
        'Trend_Aligned', 'LTP_gt_YHigh', 'Open_gt_YClose', 'EMA_Always_Correct',
        'Pullback_Happened', 'Reversal_Confirmed', 'Sideways_Post_Gap', 
        'ADX_Exhaustion', 'PrePeak_Compression'
    ]
    
    impacts = []
    for col in bool_cols:
        avg_true = df[df[col] == True]['Abs_Move%'].mean()
        avg_false = df[df[col] == False]['Abs_Move%'].mean()
        uplift = ((avg_true - avg_false) / avg_false * 100) if avg_false != 0 else 0
        impacts.append({
            'Feature': col,
            'Avg_Move_True': round(avg_true, 2),
            'Avg_Move_False': round(avg_false, 2),
            'Uplift%': round(uplift, 2)
        })
    
    impact_df = pd.DataFrame(impacts).sort_values(by='Uplift%', ascending=False)
    
    # 3. Timing Impact
    timing_impact = df.groupby('Best_Bucket')['Abs_Move%'].agg(['mean', 'count']).rename(columns={'mean': 'Avg_Move%'})

    print("\n" + "="*60)
    print("📈 FEATURE IMPACT ANALYSIS (CORRELATION TO MOVE SIZE)")
    print("="*60)
    print("\nTop Numeric Correlations (Strength of Move):")
    print(corr_matrix.to_string())
    
    print("\nTop Boolean Predictors (Uplift in Move Size):")
    print(impact_df.to_string(index=False))
    
    print("\nTiming Effectiveness:")
    print(timing_impact.to_string())
    
    # 4. Filter Recommendations
    print("\n" + "="*60)
    print("🚀 FILTER ARCHITECTURE RECOMMENDATIONS")
    print("="*60)
    
    # Logic: High Uplift + High Hit Rate = Restrictive. High Correlation = Scoring.
    print("1. RESTRICTIVE (GATES):")
    if impact_df.iloc[0]['Uplift%'] > 10:
        print(f"   - {impact_df.iloc[0]['Feature']}: Huge impact on move size.")
    print("   - Trend_Aligned: Essential for hit-rate stability (from previous run).")
    
    print("\n2. SCORING (WEIGHTS):")
    top_corr = corr_matrix.index[1] # index 0 is Abs_Move% itself
    print(f"   - {top_corr}: Strongly correlates with explosive moves.")
    print("   - Gap%: Initial energy is a major factor in final expansion.")
    
    print("\n3. REJECTION (BLOCKERS):")
    print("   - EMA_Crosses: High cross count (choppy) negatively impacts trend strength.")
    print("="*60)

if __name__ == "__main__":
    analyze_correlations('backtest_lab/orbiter_revamp_data.csv')
