# 🤖 Orbiter Telegram User Guide

This guide explains how to monitor and control your trading bot using Telegram.

## 📊 Monitoring Commands

### `/status` (The Big Picture)
Use this command to get a comprehensive overview of your financial and operational state.
- **When to use:** At the start of a session or when checking overall health.
- **Output includes:** 
    - Total Buying Power (Cash + Collateral).
    - Detailed breakdown: Margin Used, Net Available, Collateral Value, Ledger Cash.
    - List of any overnight positions with their current MTM.
    - Warning if liquid cash is dangerously low.

### `/margin` (Quick Wallet Check)
A concise snapshot of your current margin status.
- **When to use:** Right before taking a manual trade or to verify if the bot has enough room for another position.
- **Output includes:** Available margin, Used margin, and Ledger balance.

### `/scan` (Live Market Pulse)
Provides a real-time view of the bot's internal scanner and open portfolio.
- **When to use:** During active market hours to see "what the bot is thinking."
- **Output includes:**
    - Total number of symbols being scanned.
    - **Top 10 Scans:** Symbols with the highest absolute filter scores (Potential entries).
    - **Active Positions:** Detailed P&L for every open trade.
    - **Portfolio P&L:** Consolidated total profit/loss for the session.

---

## 🛠️ Administrative Commands

### `/cleanup` (Reset Google Sheets)
Resets the trade logs, active positions, and scan metrics tabs in your Google Spreadsheet.
- **Safety Feature 1:** Blocked during active trading sessions to prevent accidental data loss.
- **Safety Feature 2 (2-Step Confirm):** Sending `/cleanup` will trigger a warning. You must send `/confirm_cleanup` within 60 seconds to proceed.
- **Tabs Reset:** `trade_log`, `active_positions`, `closed_positions`, `scan_metrics`.
- **Tabs Preserved:** `control` and `symbols` are **not** affected.

---

## 🔔 Automated Notifications
The bot will automatically ping you for the following events:
1.  **Session Prep:** Sent at market open (9:30 AM NFO / 5:30 PM MCX).
2.  **Trade Alerts:** Sent immediately when a position is opened or closed.
3.  **Post-Trade Margin:** Sent immediately after any trade alert to show remaining buying power.
4.  **Session Debrief:** Sent at market close with total realized P&L and estimated T+1 margin.
5.  **Critical Errors:** Real-time alerts for connectivity or execution failures.
