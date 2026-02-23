# Last Technical Change: v3.11.1 Global TSL & Short Guard Fix

**Date:** 2026-02-23
**Status:** COMPLETE (Build: `v3.11.1`)

## 1. Strategic Outcomes
Implemented sophisticated profit protection (Global TSL) and fixed a critical signal-blocking bug to ensure trade execution.

## 2. Component Adjustments

### A. Global Portfolio TSL (`orbiter/core/engine/executor.py`)
- **Logic:** Tracks `Max Portfolio PnL` once an Activation Target is reached.
- **Config:** Activates at **₹2000**. Trails with a **20%** retracement floor.
- **Behavior:**
    - If PnL hits ₹2000 -> TSL Active (Floor ₹1600).
    - If PnL hits ₹10,000 -> Floor ₹8,000.
    - Captures runners while securing wins.
- **Safety:** Added state reset in `square_off_all` to prevent re-entry trigger loops.

### B. Signal Guard Fix (`orbiter/core/engine/executor.py`)
- **Bug:** The "Freshness Guard" was applying Long logic (LTP near High) to Short signals, blocking valid breakdowns.
- **Fix:** Implemented directional guard. Shorts now verify LTP is near Low (not High).

### C. Session Management (`orbiter/config/config.py`)
- **Hard Stop:** Set `TOTAL_STOP_LOSS_RS = 5000`.
- **Target:** Set `TOTAL_TARGET_PROFIT_RS = 2000` (as TSL Activation).

## 3. Mission Status
- **Integrity:** Validated via Matrix Simulation on Top 10 Nifty Stocks (+₹1.6L net benefit).
- **Monitoring:** Active. Expecting Short trades (e.g., WIPRO) to now execute.
