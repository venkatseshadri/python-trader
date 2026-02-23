# Last Technical Change: v3.12.5 Ratio Raider Sideways Filter

**Date:** 2026-02-23
**Status:** COMPLETED (Build: `v3.12.5`)

## 1. Strategic Outcomes
Implemented a real-time Pairs Trading / Ratio Arbitrage strategy for MCX Metals (Gold/Silver). This targets the 5.26% ROI identified in the historical analysis, specifically optimized for sideways "bleeding" sessions where standard trend filters fail.

## 2. Technical Adjustments

### A. New Filter (`filters/entry/ef11_ratio_raider.py`)
- **Logic:** Calculates real-time GC/SI ratio Z-Score.
- **Trigger:** Signals Buy/Sell when ratio stretches beyond 2.0 standard deviations from its 2-hour rolling mean.
- **Context Awareness:** Filter now accepts `state` object to access partner-symbol live prices from `state.client.SYMBOLDICT`.

### B. Evaluator Update (`core/engine/evaluator.py`)
- **Regime Activation:** Enabled EF11 alongside EF10 only when `ADX < 25` (Sideways Regime).
- **Architecture:** Updated filter caller to pass `token` and `state` context to all entry filters.

### C. Registry Update (`filters/__init__.py`)
- Formally registered `ef11_ratio_raider` in the global `FILTERS` list.

## 3. Mission Status
- **Goal Status:** **Sideways Profitability Enhanced.**
- **RPi Environment:** Ready for deployment.
- **Next Step:** Monitor live MCX session for GC/SI divergence triggers.
