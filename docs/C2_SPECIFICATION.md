# 🕹️ Orbiter Command & Control (C2) Specification

This document defines the architecture and command set for remote management of the Orbiter bot via Telegram.

## 🏗️ Architecture: RuntimeConfig Manager
To support real-time changes without code restarts, we will implement a `RuntimeConfig` singleton.
- **Location:** `orbiter/core/config_manager.py`
- **Mechanism:** A thread-safe dictionary that overrides hardcoded constants in `orbiter/filters/`.
- **Persistence:** Changes are held in memory. A `/save` command will flush them to `orbiter/data/session_config.json`.

---

## 🛠️ Command Set: Entry Filters

### F1: Opening Range Breakout (ORB)
- **Command:** `/f1 <param> <value>`
- **Parameters:**
    - `weight`: (int) Change score weight (default: 25).
    - `buffer`: (float) Adjust ORB high/low buffer percentage (default: 0.2).
    - `mom_weight`: (float) Change momentum vs distance balance.

### F2: Price vs EMA5 Distance
- **Command:** `/f2 <param> <value>`
- **Parameters:**
    - `period`: (int) Change EMA lookback (default: 5).
    - `weight`: (int) Change score weight (default: 20).

### F3: EMA5 vs EMA9 Gap
- **Command:** `/f3 <param> <value>`
- **Parameters:**
    - `short_ema`: (int) Fast EMA period (default: 5).
    - `long_ema`: (int) Slow EMA period (default: 9).
    - `weight`: (int) Change score weight (default: 18).

### F4: SuperTrend Stability
- **Command:** `/f4 <param> <value>`
- **Parameters:**
    - `period`: (int) ST lookback (default: 10).
    - `multiplier`: (float) ST sensitivity (default: 3.0).
    - `anchor_lookback`: (int) Candles for "Anchor" direction (default: 15).
    - `momentum_lookback`: (int) Candles for "Momentum" slope (default: 5).

### F5 & F6: EMA Scope & Gap
- **Command:** `/f5 <param> <value>` or `/f6 <param> <value>`
- **Parameters:**
    - `window`: (int) Change evaluation lookback (default: 5 mins).
    - `scale`: (int) Change the multiplier for the raw score (default: 5 for F5, 20 for F6).
    - `noise`: (float) Adjust the absolute noise threshold (default: 0.05).
    - `cap`: (float) Change the max score cap (default: 0.20).

### F7: ATR Relative Volatility
- **Command:** `/f7 <param> <value>`
- **Parameters:**
    - `bonus_thresh`: (float) Rel-Vol threshold for +0.10 bonus (default: 1.10).
    - `penalty_thresh`: (float) Rel-Vol threshold for -0.10 penalty (default: 0.75).

### F8: Trend Sniper
- **Command:** `/f8 <param> <value>`
- **Parameters:**
    - `adx_thresh`: (int) Minimum ADX for gatekeeping (default: 25).
    - `score`: (float) The score assigned when ADX > threshold (default: 0.25).

---

## 🛡️ Command Set: Exit & Risk (SL/TP)

### F1: Profit Taking (TP)
- **Command:** `/tp fix <param> <value>`
- **Parameters:**
    - `decay_pct`: (float) Target decay % of short premium (default: 10.0).
    - `cash_rs`: (int) Absolute cash profit target (default: from config).

### F2: Trailing Stop Loss (TSL)
- **Command:** `/tp trail <param> <value>`
- **Parameters:**
    - `activation`: (float) Profit % to start trailing (default: 5.0%).
    - `step`: (float) SL increase per 1% profit increase (default: 1.0).
    - `buffer`: (float) Distance from max profit (default: 5.0).

### F3: PnL Retracement SL
- **Command:** `/tp retrace <param> <value>`
- **Parameters:**
    - `pct`: (int) Allowed % drop from peak PnL (default: 50).
    - `activation_rs`: (int) Cash profit required to activate (default: 1000).

### SL Filters (Breakouts & Indicators)
- **Command:** `/sl <id> <param> <value>`
- **Parameters:**
    - `orb_buffer`: (float) Buffer for F3 ORB-Low break (default: 0.02).
    - `vwap_mult`: (float) Sensitivity for F8 VWAP exit (default: 0.998).
    - `st_period`: (int) SuperTrend SL period (default: 10).
    - `st_mult`: (float) SuperTrend SL multiplier (default: 3.0).

---

## 🚦 Operational Commands

- `/status`: Returns a summary of:
    - Current Segment (NFO/MCX).
    - Active Filter Scores for the top 3 watched symbols.
    - P&L of open positions.
    - Runtime overrides currently active.
- `/filter <id> enable|disable`: Hot-toggle any filter file.
- `/kill`: Closes all positions at market price and enters Hibernation.
- `/resume`: Exits Hibernation and resumes scanning.
- `/watch <symbol>`: Forces the bot to track a symbol even if not in the primary universe.

---

## 🔐 Security & Validation
- **Auth:** Only process commands from `ALLOWED_CHAT_IDS` (e.g., `8317944043`).
- **Sanity Checks:** All numeric inputs must fall within hardcoded "Safety Envelopes" (e.g., Max TP cannot exceed 95%, Max SL cannot exceed 50%).
