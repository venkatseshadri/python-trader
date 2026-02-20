# 🏗️ Orbiter Architecture & Key Decisions

## Core Components

1.  **`main.py` (Controller):**
    - Determines Active Segment (NFO vs MCX) based on time.
    - Initializes `BrokerClient` (specific to the segment).
    - Runs the infinite loop (Evaluation -> Execution -> Sync).

2.  **`core/broker/__init__.py` (BrokerClient):**
    - **The Source of Truth.** Do NOT edit `core/client.py` (Deprecated).
    - Wraps `ShoonyaApiPy`.
    - Manages `SYMBOLDICT` (Live Data).
    - Delegated Logic:
        - `master/`: Loads Scrip Masters and Custom Maps.
        - `executor/`: Handles Order Placement logic.
        - `resolver/`: Resolves Symbols (Future/Option chains).

3.  **`core/engine/executor.py`:**
    - Consumes signals and routes orders.
    - **UX Layer:** Consolidates multiple signals into a single "Batch Entry" notification to prevent Telegram spam during high-volatility windows.
    - **Logic:** Integrates real-time margin data from `SummaryManager` directly into consolidated alerts.

4.  **`core/analytics/summary.py` (SummaryManager):**
    - **Purpose:** Centralizes all financial and performance calculations.
    - **Funds Logic:** Provides authoritative "Available Liquidity" for the C2 notification layer.
    - **Tax Logic:** Calculates estimated Net P&L using segment-specific tax/brokerage rates.

5.  **`utils/telegram_notifier.py` (C2 System):**
    - **Listener:** Runs an async background thread to poll for commands.
    - **Safety:** Implements session-awareness to block critical actions during market hours.

## 🛡️ Live Core vs. Research Separation

To maintain 99.9% uptime during market hours, the project enforces a strict boundary between execution and research:

### 1. Live Core (Orbiter)
- **Directories:** `orbiter/`, `config/`, `ShoonyaApi-py/`.
- **Status:** Mission Critical.
- **Update Policy:** Triggers a daemon restart via `update.sh` to apply new logic.

### 2. Research & Lab (Sniper / Docs)
- **Directories:** `backtest_lab/`, `docs/`, `samples/`.
- **Status:** Non-Critical.
- **Update Policy:** Updates do NOT trigger a daemon restart. Research can be synced live without interrupting active trading sessions.

---

## 🧠 State Memory & Guarded Execution

To ensure stability across system restarts and prevent over-trading, the system implements a persistent state-aware execution layer:

### 1. Session Persistence (Disk-based Memory)
- **Mechanism:** `OrbiterState.save_session()` and `load_session()`.
- **Storage:** `orbiter/data/session_state.json`.
- **Atomic Integrity:** Uses a "Write-then-Swap" pattern. Data is written to `.tmp` and then atomically renamed to the primary file. This prevents corruption during power failure or process crashes.
- **Sanitization:** The state saver automatically strips non-serializable Python objects (like module loaders or active API objects) from the state dictionary before saving, ensuring JSON integrity.
- **Freshness Protocol:** 
    - **Expiry:** If the state file is >30 minutes old, it is considered "stale" and discarded.
    - **Corruption Recovery:** If a malformed JSON file is detected on startup, it is automatically backed up to `.corrupt` for forensics and the bot starts fresh.
    - **Silent Recovery:** Recovered positions do NOT trigger new Telegram notifications.

### 2. Score Velocity (Momentum Tracking)
- **Logic:** The `Executor` compares the current signal score against the `opening_score`.
- **Log Format:** `Score: 1.25 (+0.20)` indicates the stock is becoming "trendier" as the session progresses.
- **Purpose:** Identifies if momentum is accelerating (positive velocity) or fading (negative velocity).

### 3. Trend-State Entry Guards
Even if a signal score is high, the `Executor` performs two "Real-time Sanity Checks" before opening a position:
- **Slope Guard:** Uses a 1-minute EMA5. Re-entry is blocked unless the current EMA5 is higher than its level 5 minutes ago (`EMA5_now > EMA5_prev`). This ensures the trend is actively moving up.
- **Freshness Guard:** Blocks entries if the current price is stagnant. Price must be within **0.2% of the session high** to qualify as a fresh breakout.

---

## 🧠 Critical Logic: MCX Token Resolution

We faced persistent `future_not_found` errors because `place_future_order` was receiving prefixed tokens (`MCX|477167`) but the map only contained raw IDs (`477167`), or vice-versa.

**The Fix:** "Dual-Key" Strategy in `ScripMaster.load_segment_futures_map`.
- We store **both** versions in `TOKEN_TO_SYMBOL`.
    - `'477167': 'COPPER27FEB26'`
    - `'MCX|477167': 'COPPER27FEB26'`

**The Fix:** Priority Lot Size Lookup in `BrokerClient.place_future_order`.
1.  **Priority 0:** Check `SYMBOLDICT` (Live WS). If the feed is live, it contains the authoritative `ls` (Lot Size).
2.  **Priority 1:** Check `TOKEN_TO_LOTSIZE` (Memory Cache). Populated from `mcx_futures_map.json` at startup.
3.  **Priority 2:** Check `DERIVATIVE_OPTIONS` (Master File).

## 🛠️ Utilities
- `utils/mcx/update_mcx_config.py`:
    - Connects to Shoonya.
    - Finds nearest futures.
    - **Captures Lot Size** and saves to `data/mcx_futures_map.json`.
    - Updates `config/mcx/config.py` with the universe list.

## 📈 Transparency & Monitoring

The bot provides high-resolution logging to allow for forensic audit of every decision:

### 1. Dual-Metric Position Tracking (Smart SL V2)
To eliminate "Leverage Divergence" (where tiny stock moves trigger huge option premium swings), the system uses a split-source risk model:
- **Trend Gauge (Underlying %):** Technical Stop Losses (EMA20, SuperTrend) are calculated using the **Underlying Stock Price (LTP)**. 
- **Volatility-Aware SL (ATR):** The bot calculates the stock's **ATR (Average True Range)** at the moment of entry. 
    - **Futures:** SL is set at `Entry +/- 1.5 * ATR`.
    - **Spreads:** Premium SL is set at `Entry_Premium + (0.25 * ATR)`. This ensures the buffer is proportionate to the stock's actual "breathing room."
- **Profit Gauge (Cash PnL ₹):** Trailing Stop Losses are calculated using **Hard Cash (Rupee) values**. Milestone-based trailing (e.g., lock in ₹500 once ₹2000 is hit) provides stable risk management.

### 2. Consolidated Alerts (Brevity Protocol)
To ensure high signal-to-noise for the trader:
- **Batch Entries:** Multiple position opens in a single cycle are batched into one concise message including **Score Velocity** and **Total Margin**.
- **Exit Summary:** SL/TP hits are aggregated into a single detailed message displaying `[Stock %]` and `(₹PnL)`.
- **Spam Suppression:** Redundant, line-by-line margin alerts have been eliminated in favor of integrated liquidity status.

---

## ⚠️ Gotchas
- **`core/client.py` is DEPRECATED.** It is a monolithic legacy file. Do not edit it. The active code is in `core/broker/`.
