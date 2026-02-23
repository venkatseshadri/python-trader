# Last Technical Change: v3.12.7 Futures-Optimized Ratio Raider

**Date:** 2026-02-23
**Status:** COMPLETED (Build: `v3.12.7`)

## 1. Strategic Outcomes
Optimized the Ratio Arbitrage strategy for the high-liquidity MCX Futures market. This follows a liquidity audit confirming that MCX options are currently untradeable for scalping. The refined filter now captures faster divergences between Gold/Silver and Copper/Aluminum.

## 2. Technical Adjustments

### A. Filter Refinement (`filters/entry/ef11_ratio_raider.py`)
- **Time Sensitivity:** Reduced rolling Z-score window from 120m to 60m for faster entry in volatile evening sessions.
- **Symbol Expansion:** Added industrial metal pairing (`COPPER` / `ALUMINIUM`).
- **Precision Logic:** Standardized ratio calculation (Primary vs Partner) to ensure consistent Buy/Sell signals across paired assets.

### B. Instrument Pivot
- Shifted strategy focus exclusively to **Futures** for the MCX segment due to verified option illiquidity.

## 3. Mission Status
- **Goal Status:** **MCX Sideways Strategy Hardened.**
- **RPi Environment:** Deploying v3.12.7 for final session observation.
- **Next Step:** Monitor for Futures ratio trades in the 21:00-23:30 window.
