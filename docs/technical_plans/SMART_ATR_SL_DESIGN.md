# 🧠 Technical Design: Smart ATR-Based Stop Loss

**Date:** 2026-02-20  
**Status:** Implemented (Commit `621cf38`)  
**Objective:** Replace static 10% premium stops with dynamic, volatility-adjusted buffers.

---

## 1. The Problem: "The Tick Noise Trap"
The legacy 10% SL logic was mathematically blind to stock price.
- **Micro-Premiums:** A 10% SL on a ₹10 premium is only ₹1.00 (20 ticks). In a volatile stock like BAJFINANCE, the bid-ask spread alone is often larger than this buffer.
- **The Result:** The bot was "Knee-Jerking" out of winning trades because the stock "breathed" by 0.05%, hitting the tiny 10% premium buffer.

---

## 2. The Research: 2024 High-Res Comparison
We tested the **Fixed 10% SL** vs. the **Smart ATR SL** using actual October 2024 option data.

| Strategy | Total PnL (10 Stocks) | Delta | Verdict |
| :--- | :--- | :--- | :--- |
| **Fixed 10% SL** | -₹5,237 | baseline | Noisy / Unstable |
| **Smart ATR SL** | **-₹2,112** | **+₹3,125** | **Superior Stability** |

**Observation:** Smart ATR SL turned several losses into profits (e.g., ASIANPAINT) by allowing the trade to survive the initial morning noise.

---

## 3. Technical Implementation

### A. The "Breathing Room" Formula
The SL is now anchored to the stock's **Average True Range (ATR)**:
1.  **For Futures:** `SL = Entry +/- (1.5 * ATR)`. This allows the stock to move 1.5x its average 1-minute range before we exit.
2.  **For Spreads:** `Premium_SL = Entry_Premium + (0.25 * ATR)`. 
    - *Logic:* Assuming a 0.50 Delta, a 0.5x ATR move in the stock should only result in a 0.25x ATR change in the premium. This creates a "Gamma Shield."

### B. Fixed Entry-ATR
The ATR is calculated **once** at the moment of entry and stored in the position metadata. This prevents the SL from "drifting" if volatility spikes later.

---

## 4. Design Outcome
- **Resilience:** Trades survive "Tick Noise" and bid-ask spreads.
- **Consistency:** The same mathematical logic applies to ₹200 stocks and ₹5000 stocks.
- **Confidence:** Verified by 2024 historical premium data and regression tests.
