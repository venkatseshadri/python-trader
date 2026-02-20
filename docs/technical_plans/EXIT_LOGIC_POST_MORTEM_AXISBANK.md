# 📉 Post-Mortem: AXISBANK Profit Erosion (2026-02-20)

**Trade ID:** NFO|59215  
**Strategy:** PUT_CREDIT_SPREAD  
**Outcome:** Negative Exit (₹-31.25) after +5.23% Peak Profit.

---

## 1. Step-by-Step Execution Log

| Time | Action | Price | PnL% | Logic State |
| :--- | :--- | :--- | :--- | :--- |
| 13:56:55 | **OPEN** | 1372.2 | 0.00% | Initial Entry |
| 13:57:22 | MONITOR | 1373.0 | **+5.23%** | **Peak reached.** Trailing SL calculated: `5.23 - 5.0 = 0.23%` |
| 13:58:15 | MONITOR | 1372.5 | +3.92% | Profit eroding. SL threshold (0.23%) not yet breached. |
| 13:59:27 | **EXIT** | 1372.1 | **-0.65%** | **Threshold Breach.** Price dropped through 0.23% directly to -0.65% within a 5s scan cycle. |

---

## 2. Technical Failure Analysis

### A. The "Activation Buffer" Flaw
The current filter `tf2_trailing_sl.py` uses a static 5% offset: `trailed_sl = max_profit - 5.0`. 
- **Reasoning:** For a stock like AXISBANK, where intraday moves are often between 1-2%, waiting for a 5% swing in option premium is far too loose. By the time the 5% buffer is hit, the underlying momentum has already completely reversed.

### B. Delta Sensitivity
In a Credit Spread, the "Basis" (Short leg) is extremely sensitive to gamma/delta. A move of just ₹0.90 in the stock price caused a **~6% swing** in the spread value. The 5% buffer provided zero protection against this volatility.

### C. Execution Latency
The 5-second `UPDATE_INTERVAL` combined with the 5% buffer creates a "Death Zone." In fast markets, the price can move 1-2% *beyond* the SL before the next scan cycle executes the trade.

---

## 3. Action Plan: Strategy Pivot

1.  **Reduce Activation:** Change Trail Activation from 5% to **1.5%**.
2.  **Tighten Buffer:** Change Trail Offset from 5% to **0.75%**.
3.  **Implement Peak-Lock:** If profit exceeds 3%, lock in at least 50% of the gains regardless of the buffer.

**Conclusion:** The current trailing logic is optimized for slow-moving, low-leverage instruments. It is mathematically incompatible with the high-gamma environment of NFO Credit Spreads. **Immediate replacement required.**
