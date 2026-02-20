# 🧠 Technical Design: Smart SL V2 (Underlying-Aware Risk)

**Date:** 2026-02-20  
**Status:** Implemented (Commit `1fec0fa`)  
**Objective:** Eliminate stop-loss "noise" caused by option premium volatility and leverage.

---

## 1. The Problem: "The Gamma Robbery"
In version `v3.9.5`, the bot used **Option Premium %** for all risk management. 
- **Evidence (BAJFINANCE):** A tiny ₹0.65 move in the stock (0.06%) caused a 6.67% swing in the option spread.
- **Impact:** The bot saw a "5% drop" and triggered a Trailing SL, even though the stock was still technically trending perfectly. This led to "Green-to-Red" round-trips where a ₹400 profit became a ₹75 loss.

---

## 2. The Design Shift: Split-Source Risk

| Gauge | Source of Truth | Used For | Why? |
| :--- | :--- | :--- | :--- |
| **Trend Gauge** | **Underlying LTP** | Technical SL (EMA20, ST) | Matches charts and institutional volume. |
| **Profit Gauge** | **Cash PnL (₹)** | Trailing SL & Targets | Hard money doesn't lie. It ignores gamma noise. |

---

## 3. Technical Implementation

### A. Cash-Based Trailing (V2)
The Trailing SL filter (`f2_trailing_sl.py`) no longer looks at `%`. It follows the money:
1.  **Activation:** Starts at a Rupee milestone (e.g., ₹1000).
2.  **Retracement:** Exits if profit drops by X% (default 40%) from the peak cash PnL reached.
3.  **Peak-Lock:** If Peak PnL crosses ₹2000, the bot locks in a floor of ₹500. It is physically impossible for a successful trade to end in a loss after hitting this threshold.

### B. Consistent PnL Tracking
The `Executor.check_sl` loop now calculates `pnl_rs` (Total Rupees) for every position, every 5 seconds. This unified metric is used for both individual exits and the **Portfolio-wide Target/SL**.

---

## 4. Design Outcome
- **Stability:** Stop-losses are no longer triggered by wider bid-ask spreads or temporary IV spikes.
- **Clarity:** Notifications now match the stock chart: `[Stock: +0.50%] (₹600.00)`.
- **Profitability:** By "Locking the Green," the bot's win-rate floor is significantly elevated.
