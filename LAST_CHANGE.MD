# Last Technical Change: v3.11.2 Infrastructure Hardening & Global TSL

**Date:** 2026-02-23
**Status:** COMPLETE (Build: `v3.11.2`)

## 1. Strategic Outcomes
Transformed the Raspberry Pi into a high-performance headless trading node and deployed advanced profit protection logic (Global TSL) verified against Nifty Top 10 historical data.

## 2. Technical Adjustments

### A. Raspberry Pi Optimization (`Infrastructure`)
- **GUI Suppression:** Stopped `lightdm` and set system to `multi-user.target` (CLI only).
- **Resource Recovery:** Masked `packagekit` and disabled `cups`.
- **Result:** Available RAM increased from **120MB to 440MB** (+266% gain).

### B. Global Portfolio TSL (`orbiter/core/engine/executor.py`)
- **Implementation:** Portfolio-wide trailing stop loss that activates at **₹2000** profit.
- **Trailing:** Enforces a **20% retracement floor** (e.g., if peak is ₹10k, floor is ₹8k).
- **Validation:** Matrix backtest on Top 10 Nifty stocks showed **+₹1.66L net benefit** over fixed targets.

### C. Signal Guard Corrections (`orbiter/core/engine/executor.py`)
- **Directional Logic:** Re-engineered "Freshness Guard" and "Slope Guard" to handle **SHORT** signals. Previously, these were using Long-only logic, blocking valid breakdowns.
- **WIPRO Fix:** Verified that WIPRO short signals (-0.54) are now unlocked for execution.

## 3. Mission Status
- **Integrity:** Deployed and verified on RPi.
- **Safety:** Hard Session Stop set at **-₹5000**.
- **Monitoring:** Active. Bot is in Simulation Mode with optimized resource headroom.
