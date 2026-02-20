# 🧠 Technical Design: Relative Freshness Guard (15m Window)

**Date:** 2026-02-20  
**Status:** Implemented (Commit `a5c8466`)  
**Objective:** Prevent entry paralysis during late-session trends by making the breakout rule relative to recent price action instead of the entire day.

---

## 1. The Problem: "The Morning Peak Trap"
In multi-session instruments like MCX (Commodities), a high made at 10 AM remains the "Day High" until 11:30 PM.
- **Legacy Logic:** `if ltp < Day_High * 0.998: skip`.
- **Result:** If SILVER hit 2.55L at 10 AM, and a new trend started at 7 PM at 2.53L, the bot would **Refuse to Enter** because it was still >0.2% below the 10 AM peak. This ignored the fact that the evening move was a valid, fresh trend in its own right.

---

## 2. Technical Modifications (`executor.py`)

### A. The 15-Minute Anchor
The bot now calculates the **Recent High** using the last 15 one-minute candles:
`recent_high = max(highs_raw[-15:])`

### B. The 0.2% Buffer
The entry gate is now:
`if ltp < recent_high * 0.998: skip`
- This ensures the bot is still buying "Strength" (near the local peak) but is no longer "haunted" by the early morning high.

---

## 3. Design Outcome
- **Increased Opportunity:** The bot can now capture mid-day pullbacks and evening commodity surges.
- **Trend Purity:** It still prevents buying into "sideways garbage" by requiring the price to be at its local 15-minute maximum.
- **Verification:** Regression tests in `test_executor_logic.py` confirm the guard passes if price matches the 15-minute high.
