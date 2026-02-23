# Hybrid Regime Engine Research & Implementation
**Date:** 2026-02-23
**Status:** IMPLEMENTED (Build v3.12.0)

## 1. Objective
Enable the bot to profit from BOTH trending and sideways markets concurrently by dynamically switching strategies per stock based on the local market regime.

## 2. The Logic (Regime Switching)
For every stock in every scan cycle:
1.  **Indicator:** Calculate **ADX(14)** using the last 15-30 minutes of data.
2.  **Decision Tree:**
    - **SIDEWAYS (ADX < 25):** 
        - Strategy: **Range Raider** (Mean Reversion).
        - Logic: Buy below Lower BB, Sell above Upper BB.
        - Risk: Tight SL (0.25x ATR).
    - **TRENDING (ADX >= 25):**
        - Strategy: **Orbital** (Breakout).
        - Logic: ORB Breakout + EMA Alignment.
        - Risk: Normal SL (1.5x ATR).

## 3. Component Changes

### A. Evaluator (`orbiter/core/engine/evaluator.py`)
- Integrated `talib.ADX` calculation.
- Implemented dynamic weight override based on regime.
- In Sideways mode, all weights are zeroed except for `ef10_range_raider`.

### B. Filters (`orbiter/filters/entry/f10_range_raider.py`)
- New filter class implementing Bollinger Band Extremes (+/- 0.51 score).

### C. Executor (`orbiter/core/engine/executor.py`)
- Now regime-aware.
- Sets `sl_mult` dynamically (0.25 for sideways, 1.5 for trending).
- Stores `regime` label in position state for forensic analysis.

## 4. Expected Outcome
- **Increased Trade Frequency:** Captures micro-moves during market lulls.
- **Improved Equity Curve:** Sideways wins offset trending "chop" losses.
- **Diversification:** Some stocks may be trending (e.g., WIPRO) while others consolidate (e.g., RELIANCE); both are now tradable.
