# Last Technical Change: v3.12.0 Hybrid Regime Engine Deployment

**Date:** 2026-02-23
**Status:** COMPLETE (Build: `v3.12.0`)

## 1. Strategic Outcomes
Successfully implemented a "Stock-Specific Regime Switcher," allowing the bot to profit from both trending and sideways stocks simultaneously. This addresses the user's challenge to be creative in sideways markets without sacrificing trend capture.

## 2. Technical Adjustments

### A. Hybrid Evaluator (`orbiter/core/engine/evaluator.py`)
- Integrated real-time **ADX(14)** calculation per stock.
- **Dynamic Weighting:** 
    - **ADX < 25 (Sideways):** Activates `Range Raider` mean-reversion logic.
    - **ADX >= 25 (Trending):** Activates `Orbital` breakout logic.
- Log output now displays `[SIDEWAYS ADX:xx.x]` or `[TRENDING ADX:xx.x]` for every evaluation.

### B. Range Raider Filter (`orbiter/filters/entry/f10_range_raider.py`)
- New filter class that identifies Bollinger Band (20, 2) extremes.
- Scores +0.51 (Buy) or -0.51 (Sell) at extremes to trigger mean-reversion trades.

### C. Adaptive SL Management (`orbiter/core/engine/executor.py`)
- Implemented **Regime-Aware Risk:**
    - Sideways trades use a tight **0.25x ATR** multiplier.
    - Trending trades use a standard **1.5x ATR** multiplier.

## 3. Mission Status
- **Integrity:** Deployed and verified on RPi.
- **Goal:** Targets >₹5000 profit by harvesting the sideways chop while waiting for trend breakouts.
- **Monitoring:** Active.
