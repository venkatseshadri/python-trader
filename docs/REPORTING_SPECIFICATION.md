# 📊 Orbiter Reporting Specification

This document defines the automated session-start and session-end reporting requirements.

## 🌅 Pre-Session Summary (9:30 AM NFO / 5:30 PM MCX)
The goal is to confirm the bot is "Ready for Battle" with clear financial context.

### Data Points:
- **Broker Connectivity:** Status of Shoonya API handshake.
- **Fund Snapshot:** 
    - Cash Balance.
    - Utilized Margin (for overnight positions).
    - Net Available Margin.
- **Overnight Positions:**
    - List of open scrips, quantities, and entry prices.
    - Current Unrealized P&L at market open.
- **Universe Status:** Number of symbols in the watch-list for the current segment.
- **Health Check:** Disk space on RPi and local database integrity status.

---

## 🌇 Post-Session Summary (3:30 PM NFO / 11:30 PM+ MCX)
The goal is a comprehensive "Debrief" of the day's performance.

### Data Points:
- **Session Performance:**
    - Total Trades Taken.
    - Realized P&L (Gross).
    - **Estimated Net P&L:** (Gross P&L - Estimated Taxes/Brokerage).
- **Portfolio Snapshot:**
    - Final status of all positions (Closed/Square-off).
    - Remaining open positions (if any).
- **Financial Integrity:**
    - Remaining Margin.
    - **T+1 Estimates:** Estimated margin receivable/deductable for next session.
    - Cash Margin impact from equity trades.
- **Execution Quality:**
    - Average Slippage (Signal vs. Executed).
    - Hit Rate of filters (which filter triggered most entries today).
- **System Logs:** Count of Warnings/Errors encountered during the session.

---

## 🛠️ Implementation Plan
1. **Analytics Engine:** Create `orbiter/core/analytics/summary.py` to calculate session-wide metrics.
2. **Lifecycle Hooks:** Integrate calls in `main.py` before the evaluation loop starts and before hibernation begins.
3. **Telegram Templates:** Use Markdown-formatted templates for visually clean reports.
