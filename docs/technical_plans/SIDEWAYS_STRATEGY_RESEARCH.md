# Sideways Strategy Research: "The Range Raider"
**Date:** 2026-02-23
**Objective:** Capture profit during low-volatility (sideways) regimes where trend-following fails.

## 1. The Strategy (Mean Reversion)
- **Philosophy:** In a non-trending market, price oscillates between statistical extremes (Bollinger Bands) and the mean (SMA).
- **Regime Filter:** **ADX(14) < 25**. (Crucial: Prevents trading during strong trends).
- **Entry:**
    - **Long:** Close < Lower Bollinger Band (20, 2).
    - **Short:** Close > Upper Bollinger Band (20, 2).
- **Exit:**
    - **Target:** Middle Bollinger Band (SMA 20).
    - **Stop Loss:** 0.25% (Tight protection against breakouts).
- **Window:** 10:00 AM - 02:30 PM (Avoid open/close volatility).

## 2. Backtest Results (Last 60 Days | Top 10 Nifty Stocks)

| Stock | Trades | Win Rate | Net PnL (1 Lot) | Avg PnL/Trade |
| :--- | :--- | :--- | :--- | :--- |
| **BHARTIARTL** | 536 | 88.2% | **₹3,24,174** | ₹605 |
| **SBIN** | 500 | 85.8% | **₹1,72,105** | ₹344 |
| **AXISBANK** | 506 | 88.7% | **₹1,54,851** | ₹306 |
| **ICICIBANK** | 463 | 90.3% | **₹1,40,761** | ₹304 |
| **INFY** | 527 | 89.0% | **₹1,04,769** | ₹199 |
| **HDFCBANK** | 543 | 90.2% | **₹99,942** | ₹184 |
| **ITC** | 484 | 89.7% | **₹92,221** | ₹191 |
| **LT** | 518 | 85.5% | **₹85,241** | ₹165 |
| **TCS** | 526 | 87.8% | **₹66,863** | ₹127 |
| **RELIANCE** | 571 | 88.6% | **₹63,148** | ₹111 |

**💰 TOTAL PROFIT: ₹13,04,074** (across 5174 trades)

## 3. Analysis
- **High Frequency:** Avg ~8.6 trades/day per stock.
- **High Accuracy:** ~88% Win Rate. The "Return to Mean" is highly reliable in low ADX.
- **Micro-Wins:** Avg profit per trade is small (₹100 - ₹600), but volume drives the PnL.
- **Risk:** If a breakout occurs (ADX spikes), the 0.25% SL protects capital.

## 4. Recommendation
- This strategy is the perfect **hedge** to the main Trend Following (Orbital) strategy.
- **Implementation:** Can be added as a "Regime-Switching" module. If ADX < 25, run Range Raider. If ADX > 25, run Orbital.
