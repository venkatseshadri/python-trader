# 🛡️ NIFTY 1% Mover Research Summary (Feb 19, 2026)

## 🎯 Objective
Reverse-engineer "Institutional Footprints" by analyzing every NIFTY 100 stock that moved ≥1% over the last 50 trading days (1,941 unique events).

## 🔬 Core Discoveries (Top 3 Patterns)
We identified three high-probability technical signatures:
1. **The Breakout King:** `STRONG_ADX` + `VOL_EXP_READY` + `YLOW_BREAK`. Shorting when momentum and volatility expansion align with a level break.
2. **The Institutional Trap:** `BULL_FLIP` + `STRONG_ADX` + `YHIGH_BREAK`. Longing after a Red day when yesterday's High is recovered (1.96% average move).
3. **The Structural Trend:** `STRUCT_ALIGN` + `STRONG_ADX` + `YLOW_BREAK`. Direction aligned with Daily EMA 50/100 (Lowest drawdown risk: 31%).

## 🛠️ Technical Implementation
- **Enhanced Extraction:** `nifty_mover_analysis.py` now captures 50+ properties with mathematical "Proof" strings.
- **Advanced Exit Strategy:** Integrated 0.5% Hard SL, 85% Dynamic Profit Retention, and 3-candle Wick Reversal detection.
- **Reporting:** Created `abb_full_master_proof.html` and `attribute_analysis.html` for granular visual auditing.

## 📊 Backtest Results (Jan 2026 - 50 Stocks)
- **Initial Run:** Inflated trade count (10k+) due to logic errors.
- **Optimized Run:** 162 trades (One trade/day/stock limit).
- **Final P&L:** Rs.-5,649.00 (Reduced from -6.6M via Hard SL and timing constraints).
- **Insight:** Capital protection is solid; win rate (15%) indicates a need for higher entry precision (Wick Dominance/Volume).

## 🚀 Next Steps
- Implement "Wick Dominance" as a final entry confirmation filter.
- Analyze correlation between Gap size and Flip success rates.
- Expand study to 500 trading days once the 50-day "Pattern Alpha" filters are tuned to positive P&L.
