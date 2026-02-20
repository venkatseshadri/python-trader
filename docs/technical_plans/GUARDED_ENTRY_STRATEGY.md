# 🛡️ Technical Design: Guarded Entry & Trend Mortality

**Date:** 2026-02-20  
**Status:** Implemented (Commit `c550e5d`)  
**Objective:** Stop trade churn and eliminate 1-minute noise by aligning execution with Institutional Research laws.

---

## 1. The Problem: "The Buy-Back Loop"
Prior to this implementation, the bot suffered from **High Frequency Churn**. 
- **Symptom:** A symbol would be bought, hit a noisy 1-minute SL (like EMA5 < EMA9), exit, and then be immediately re-bought 5 seconds later because the overall 15-minute trend was still positive.
- **Impact:** High transaction costs, messy logs, and "Premature Exit Syndrome" (exiting winners too early).

---

## 2. The Research: 100-Day Study (ADANIENT & SBIN)
We compared a **Naive Entry** (LTP > ORB) against a **Guarded Entry** across 100 days.

| Metric | Naive Strategy | Guarded Strategy | Improvement |
| :--- | :--- | :--- | :--- |
| **Trade Count** | 588 total | 146 total | **75% reduction in churn** |
| **Max Drawdown** | -2.48% (ST 1m) | -1.20% (EMA20 15m) | **50% risk reduction** |
| **Win Rate** | ~35% | ~35% | No loss in quality |

---

## 3. Technical Implementation

### A. Trend-State Guards (`rank_signals`)
The bot no longer enters based solely on morning ORB levels. It now verifies the **current state** of the move:
1.  **Slope Guard:** Checks 1-minute **EMA5**. Re-entry is blocked unless `EMA5_now > EMA5_5m_ago`. This ensures we aren't buying a falling knife.
2.  **Freshness Guard:** Checks the current high. re-entry is blocked unless the price is within **0.2% of the Day High**. This prevents entering stagnant sideways drifts.

### B. Exit Cooldown (Memory)
- The system now has a **15-minute memory**.
- If a token is closed (SL or TP), it is added to `state.exit_history`.
- The bot is strictly forbidden from re-entering that specific token for 15 minutes, even if all other filters are bullish.

### C. The "Truth Indicator" (15m EMA20)
- Based on the **Law of Trend Mortality**, the bot now uses **resampled 15-minute candles** to calculate EMA20.
- A 15-minute *close* below this level is considered a final trend death (61% probability), triggering an exit. This ignores 1-minute spikes and pullbacks.

### D. Dynamic Take Profit (Total Budget Law)
- **Problem:** Fixed profit targets are unrealistic on days with a "Fat ORB" (large morning range), as the stock has already consumed most of its "Average Daily Budget."
- **Implementation (`tf4_dynamic_budget`):**
    - The bot loads `data/budget_master.json` containing the **Average Intraday Range (%)** for each stock (e.g., 4.41% for ADANIENT).
    - **Formula:** `Target = (Historical_Budget - Current_ORB_Size) * 0.75`.
    - The bot calculates a dynamic exit level for every trade. If the stock has a massive 3% ORB, the target is reduced to capture the remaining 1% move, rather than waiting for an impossible 4% extension.

---

## 5. The Persistence Layer (Anti-Amnesia)

### The Problem: The Restart Storm
Prior to version `v3.9.6`, every time the bot or Raspberry Pi restarted (due to updates or connection drops), the bot lost its in-memory record of active trades. 
- **Consequence:** On the first scan post-restart, the bot would see all signals as "New" and re-open 10+ positions, triggering a massive storm of Telegram alerts and duplicate log entries.

### The Solution: `session_state.json`
The bot now treats its memory as a persistent asset:
1.  **Continuous Saving:** Current positions and exit timestamps are flushed to disk every 5 seconds.
2.  **State Re-hydration:** On startup, the bot "re-hydrates" its memory. If a position was already active before the crash, it is silently resumed.
3.  **Freshness Check:** To avoid "Zombies" (recovering trades from hours ago when the market has moved), the bot implements a **30-minute expiry**. If the last save was over 30 minutes ago, the state is wiped for safety.

---

## 6. Final Verdict
This design shifts the bot from a "Scalper" (reacting to 1-minute noise) to a "Trend Follower" (aligned with institutional 15-minute flows). It maximizes profit by staying in trades longer and minimizes costs by stopping the churn loop.
