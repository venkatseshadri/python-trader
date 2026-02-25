# 🤖 Telegram C2 Bot (`orbiter/bot/`)

## 🎯 Single Responsibility Principle (SRP)
The `bot/` directory operates as the **Command & Control (C2) and Notification Layer**. It handles bidirectional communication between the trader (via Telegram) and the headless Orbiter daemon.

## 📂 Architecture

### 1. `notifier.py` / `telegram.py`
- **Listener:** Runs an async background thread polling for Telegram commands (`/pnl`, `/scan`, `/margin`, `/q`).
- **Publisher:** Consumes signals from the `CoreEngine` and formats them into clean, highly legible HTML messages.
- **Batching Engine:** Consolidates rapid, simultaneous trade executions into "Batched Summary" messages to prevent Telegram spam during volatile market opens.

### 2. `sheets.py`
- **Google Sheets Integration:** Publishes end-of-day reports, real-time scan metrics, and persistent logs to cloud storage for forensic analysis and performance tracking.

## 🛑 Strict Boundaries
- **No HTML Underscore Parsing Crashes:** The bot relies strictly on robust HTML tags (`<b>`, `<code>`). Markdown parsing is prohibited due to edge-case crashes with underscores in stock tickers (e.g., `M_M`).
- The bot cannot execute trades. It can only instruct the `CoreEngine` to shut down or query the `SummaryManager` for metrics.