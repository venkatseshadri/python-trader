# Global TSL Research & Matrix Simulation
**Date:** 2026-02-23
**Scope:** Top 10 NIFTY 50 Stocks (Intraday 1-Minute Data, Last 60 Days)

## 1. Objective
To validate the effectiveness of a "Global Portfolio Trailing Stop Loss" (Global TSL) against a fixed "Hard Target" profit taking strategy. The goal is to uncaps upside potential ("Let winners run") while protecting secured profits.

## 2. Methodology
- **Data:** 1-minute intraday candles for HDFCBANK, RELIANCE, ICICIBANK, INFY, TCS, ITC, LT, AXISBANK, BHARTIARTL, SBIN.
- **Simulation:** Iterate through 60 days of history. Simulate a 1-lot Long entry at 09:30 AM.
- **Mechanics:**
    - **Activation:** TSL activates when `Portfolio PnL >= Target`.
    - **Trailing:** Once active, track `Max PnL`. Set `Floor = Max PnL - (Max PnL * TSL_PCT)`.
    - **Exit:** Close all if `Current PnL <= Floor`.
- **Metrics:**
    - **Net Benefit:** (Extra Profit from Runners) - (Profit Given Back on Reversal).
    - **Win Rate:** % of days where TSL result > Hard Target result.

## 3. Results Matrix

| Target (₹) | TSL % | Net Benefit (₹) | Extra Profit (₹) | Give Back (₹) | Win Rate | Verdict |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **₹2000** | **20%** | **+₹166,807** | ₹262,042 | ₹95,235 | 49.4% | **✅ Recommended (Balanced)** |
| ₹2000 | 25% | +₹177,737 | ₹286,512 | ₹108,775 | 48.9% | Strong Aggressive |
| ₹2000 | 50% | +₹200,372 | ₹354,662 | ₹154,290 | 48.7% | ⚠️ High Volatility Risk |
| ₹5000 | 20% | +₹136,530 | ₹208,350 | ₹71,820 | 36.6% | Good, but misses smaller trends |
| ₹5000 | 50% | +₹5,698 | ₹287,975 | ₹282,277 | 34.4% | ❌ Ineffective |
| ₹10000 | 20% | +₹20,792 | ₹97,775 | ₹76,983 | 34.6% | Too high activation threshold |

## 4. Key Insights
1.  **Lower Activation is Better:** A **₹2000** activation threshold creates significantly more value (+₹1.66L) than ₹5000 or ₹10000. It allows the TSL to "latch on" to trends early.
2.  **20-25% is the Sweet Spot:** A 20% retracement captures the bulk of "Runners" (like ICICIBANK's ₹14k day) while keeping "Give Back" manageable. 50% TSL yields higher raw math but requires tolerating massive drawdowns (e.g., watching ₹10k profit drop to ₹5k).
3.  **Runners Drive Alpha:** The strategy relies on outliers. Top 5 runners contributed >50% of the extra profit.

## 5. Deployment Decision
- **Strategy:** Enable Global TSL.
- **Config:** `TOTAL_TARGET_PROFIT_RS = 2000` (Activation), `GLOBAL_TSL_PCT = 20`.
- **Status:** Code committed to `orbiter/core/engine/executor.py`. Pending Push.
