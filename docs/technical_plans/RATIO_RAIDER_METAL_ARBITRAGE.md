# Ratio Raider: Metal Arbitrage Strategy
**Date:** 2026-02-23
**Objective:** Profit from divergences between highly correlated MCX metals (Gold/Silver) during sideways "bleeding" sessions.

## 1. The Strategy (Ratio Arbitrage)
- **Philosophy:** Highly correlated pairs (GC/SI ~0.80) mean-revert when their ratio stretches beyond historical norms.
- **Regime Filter:** **ADX(14) < 25** (Sideways).
- **Metric:** Z-Score of the GC/SI Ratio (2-hour rolling window).
- **Entry:**
    - **Long Gold / Short Silver:** Ratio Z-Score < -2.0 (Gold is undervalued).
    - **Short Gold / Long Silver:** Ratio Z-Score > 2.0 (Silver is undervalued).
- **Exit:**
    - **Target:** Z-Score reverts to 0 (Mean).
    - **Stop Loss:** 0.5% Divergence expansion.

## 2. ROI Analysis (Last 5 Days | 1m Data)

| Strategy | Pair | Trades | Win Rate | Net ROI |
| :--- | :--- | :--- | :--- | :--- |
| **Ratio Arbitrage** | **GC/SI** | 37 | **70.3%** | **5.26%** |
| **BB Mean Reversion** | SI | 142 | 68.3% | 4.26% |
| **BB Mean Reversion** | GC | 150 | 48.7% | -3.75% |

**💎 KEY FINDING:** Ratio Arbitrage outperformed single-asset mean reversion by 23% and provided protection against directional "bleeding" in Gold.

## 3. Implementation Details
- **Filter:** `ef11_ratio_raider.py`
- **Mechanism:** Accesses partner LTP from `state.client.SYMBOLDICT` to calculate real-time ratio.
- **State:** Maintains a rolling ratio history in the `state` object.

## 4. Recommendation
- Deploy as a specialized MCX sideways filter to capture "Bleeding Session" recovery moves.
- Combine with `Range Raider` for multi-layered sideways profitability.
