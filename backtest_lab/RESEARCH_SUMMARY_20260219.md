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

---

## 📂 Research Artifact Index (Feb 19, 2026)

### 🛠️ Extraction & Analysis Tools (`backtest_lab/tools/`)
1.  **`extract_intraday_movers.py`**: Initial filter for >1% move days.
2.  **`extract_remaining_intraday.py`**: Batch processing for session extraction.
3.  **`generate_per_stock_csv.py`**: Creates individual session indices for each stock.
4.  **`calculate_volatility_stats.py`**: Calculates "Heartbeat%" across the universe.
5.  **`analyze_orb_correlation.py`**: Massive convergence study (ORB vs 1%).
6.  **`analyze_orb_tp_correlation.py`**: Tests "Dynamic Alpha" / Budget hypothesis.
7.  **`analyze_gap_exhaustion.py`**: Correlates gaps with reversals.
8.  **`analyze_reversal_patterns.py`**: Deep study of profit booking buckets (B1-B4).
9.  **`pattern_discovery.py`**: Mathematical identification of Top 3 signatures.
10. **`backtest_cli.py`**: The high-fidelity simulation engine (v3.9.0+).
11. **`generate_attribute_html.py`**: Global dashboard generator.
12. **`generate_comprehensive_report.py`**: Proof-based deep dive generator.
13. **`analyze_15min_purity.py`**: Quantifies noise across 15m EMA periods.
14. **`analyze_5min_purity.py`**: Quantifies noise across 5m EMA periods.
15. **`analyze_ema_recovery.py`**: Calculates recovery rates for EMA breaches.

### 📊 Consolidated Data Evidence (`backtest_lab/data/`)
- **`nifty_volatility_stats.csv`**: Heartbeat% ranking for all 105 stocks.
- **`orb_convergence_study.csv`**: 98.5% capture rate evidence.
- **`orb_efficiency_stats.csv`**: Launchpad vs. Eatup rankings.
- **`orb_tp_correlation_results.csv`**: The "Total Budget" stable-budget proof.
- **`gap_exhaustion_study.csv`**: Gap size vs. Pullback depth correlation (0.261).
- **`reversal_pattern_study.csv`**: Proof of the "1.5% Extension Rule."
- **`15min_ema_purity.csv`**: The 15m EMA20 stability proof (0.32 breaks).
- **`5min_ema_purity.csv`**: Evidence of 5m noise (9.6 breaks).
- **`ema_recovery_study.csv`**: The "Trend Mortality" proof (39% recovery on 15m EMA20).
- **`intraday1pct/`**: 250,000+ granular 1-min session JSON files.

### 🖼️ Visual HTML Reports (`backtest_lab/`)
- **`attribute_analysis.html`**: Interactive index of all 1,941 mover events.
- **`abb_full_master_proof.html`**: 50+ property deep-dive with mathematical proofs.
- **`atgl_35_properties.html`**: Initial reverse-engineering case study.
