# Core Modules

The `core/` directory is the heart of the Orbiter bot, divided into high-level broker plumbing and the execution engine.

## Subdirectories

### 1. `broker/` (The Plumbing)
An exchange-agnostic wrapper for the Shoonya API.
*   **`connection.py`**: Handles login, session tokens, and WebSocket feeds.
*   **`master.py`**: Downloads and parses Shoonya scrip masters (NSE, NFO, MCX).
*   **`resolver.py`**: The "Intelligence" that finds specific ATM strikes, expiries, and future contracts.
*   **`margin.py`**: Logic for SPAN and exposure margin calculations.
*   **`executor.py`**: low-level logic for placing multi-leg spreads and single-leg futures.

### 2. `engine/` (The Brain)
Segment-agnostic trading loop logic.
*   **`state.py`**: Manages the **`OrbiterState`**, the "Single Source of Truth" for the bot.
*   **`evaluator.py`**: Resolves candle data and calculates technical scores using the filter factory.
*   **`executor.py`**: The high-level decision maker that ranks signals and initiates trade entries or SL/TP exits.
*   **`syncer.py`**: Coordinates real-time data flow between the engine and the Google Sheets dashboard.

## 💎 The OrbiterState Object
The `OrbiterState` is the central state management object passed throughout the engine. It maintains:
- **`active_positions`**: A dictionary of currently open trades with their entry details.
- **`symbols`**: The active list of tokens being scanned.
- **`config`**: The merged runtime configuration (Strategy + Segment).
- **`last_scan_metrics`**: A buffer of the most recent evaluation results for all symbols.
- **`client`**: The reference to the `BrokerClient` for market data access.

## Segment Independence
Every class in `core/` is designed to be **exchange-agnostic**. They receive the current `segment_name` or `exchange` as parameters, ensuring that the same code handles both Equity and Commodities without modification.
