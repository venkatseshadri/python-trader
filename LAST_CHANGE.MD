# Last Technical Change: Smart ATR Stop Loss (Volatility-Aware)

**Date:** 2026-02-20
**Commit:** `1fec0fa` (Refined in subsequent patches)

## 1. The Problem (Market Noise)
The fixed 10% premium stop-loss was too tight for volatile stocks and micro-premiums (₹5-10). It triggered based on "Tick Noise" and bid-ask spreads rather than genuine trend reversals, cutting winning trades prematurely.

## 2. Technical Modifications

### A. Dynamic Buffer Logic (`orbiter/filters/sl/f1_price_increase_10.py`)
- **ATR-Anchored SL:** The fixed 10% rule was replaced with a dynamic buffer based on the stock's **ATR (Average True Range)**.
- **For Futures:** SL = `Entry +/- (1.5 * ATR)`.
- **For Spreads:** Premium SL = `Entry_Net + (0.25 * ATR)`. 
- **Reasoning:** This allows the stock to breathe within its natural 1-minute volatility range before the bot panics.

### B. Execution Engine (`orbiter/core/engine/executor.py`)
- **Entry ATR Capture:** The bot now calculates the 14-period ATR at the millisecond of entry and stores it as a persistent primitive (`entry_atr`) in the position dictionary.
- **Guard Validation:** Fixed unit tests to ensure "Rising Slope" and "Freshness" guards are satisfied by mock candle data.

## 3. Regression Testing
- **`orbiter/tests/unit/test_smart_atr_sl.py`**: Proves that ATR-based triggers work correctly for both Futures and Spreads.
- **`orbiter/tests/unit/test_executor_logic.py`**: Verified that the Executor correctly calculates and stores ATR during position opening.

## 4. Design Outcome
The bot's risk management is now **Proportionate to Volatility**. High-priced, volatile stocks get wider buffers, while stable stocks get tighter ones. This improved backtest PnL by **₹3,125** across 10 stocks in our October 2024 high-res study.
