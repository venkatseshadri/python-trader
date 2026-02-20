# 📡 Research: Telegram UX Refactor (Signal vs. Noise)

**Date:** 2026-02-20  
**Objective:** Transform Telegram from a "Log Dumper" into a "Strategic Cockpit" for a professional day trader.

---

## 1. Current Pain Points (The "Noise" Audit)

| Message Type | Frequency | Usefulness | Critique |
| :--- | :--- | :--- | :--- |
| **Position Opened** | High (Every trade) | Moderate | Too verbose. Doesn't show the *why* (Score Velocity). |
| **Margin Update** | High (After every trade) | Low | Spam. Traders care about *Total Available*, not line-by-line reduction. |
| **Positions Closed** | Moderate (per batch) | High | **Crucial.** Needs clear Stock vs. Option data (Fixed in Smart SL V2). |
| **Session Prep** | Daily | High | Good overview. No change needed. |
| **Log Alerts** | Occasional | High | Essential for system integrity. |

---

## 2. The "Smart Trader" Challenge: Brevity & Clarity

A professional trader needs to know three things instantly:
1.  **What happened?** (Direction/Action)
2.  **How much did I make/lose?** (Rupee PnL)
3.  **Is the system healthy?** (Total Margin/Errors)

### Proposed "Pulse" Notification (Consolidation)
Instead of 3 messages (Open + Margin + Margin), use **One Master Entry Alert**:
> 🚀 **LONG: JSWSTEEL** @ 1247.4
> *   **Conviction:** 1.25 (+0.20 Velocity)
> *   **Risk:** SL 1240.0 (₹-500 Max)
> *   **Liquidity:** ₹1.42L Margin Available.

---

## 3. Implementation Plan: The "Brevity Protocol"

### A. Batch Entry Notifications
If 5 positions open in 1 minute (like during a morning breakout), send **one summary** instead of 5 individual alerts.
*   *Current Status:* High spam risk during market open.
*   *Solution:* 30-second buffer. Accumulate trades and send one "Entry Batch" message.

### B. Intelligent Heartbeat
- **Currently:** Quiet until a trade happens.
- **Proposed:** If no trades occur for 1 hour, send a 1-line status:
  `💎 Orbiter Active | NFO | PnL: ₹0.00 | Top: RELIANCE (0.42)`
  *(This provides comfort that the bot is still "watching" without being laborious).*

### C. The "Obituary" Format (Exits)
Make exits even punchier.
> 🎯 **EXIT: ASIANPAINT** (₹600.00)
> *   **Trigger:** Target Hit (11.1%)
> *   **Move:** +0.50% Stock vs. +₹2.40 Spread

---

## 4. Design Verdict
The goal is to reduce message count by **60%** while increasing **Context Density by 100%**. Every message should fit on one screen of a mobile phone without scrolling.

---

## 5. Next Actions
1. [ ] Implement **Batch Entry** logic in `Executor`.
2. [ ] Suppress individual **Margin Alerts**; move them into the Entry/Exit summaries.
3. [ ] Implement the **Hourly Heartbeat** status line.
