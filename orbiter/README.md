# ORBITER v3.0 - Multi-Market Multi-Segment Trading Framework

**ORBITER** is a robust, modular trading bot designed for the Indian markets using the **Shoonya API**. It handles both **NIFTY 50 Equity Derivatives** (NFO) during the day and **Commodity Futures** (MCX) in the evening, providing a 24-hour trading solution with automated risk management and Google Sheets tracking.

## 🚀 Key Features

-   **Dual-Segment Execution**:
    -   **☀️ Day (9:15 AM - 3:30 PM)**: Trades NIFTY 50 Credit Spreads (`CREDIT_SPREAD` mode).
    -   **🌙 Evening (after 3:30 PM)**: Trades Commodity Futures (`FUTURES` mode).
-   **Modular Architecture**: Fully decoupled core engine from market-specific rules and technical filters.
-   **Advanced Risk Management**:
    -   Normalized P&L tracking (Positive = Profit) across all modes.
    -   Fixed Stop-Loss and Take-Profit targets.
    -   Dynamic Trailing SL (Locked profit after 5%).
    -   Absolute Rupee-based Portfolio Kill-switch.
-   **Granular Logging**:
    -   High-performance batch logging to Google Sheets.
    -   Segment-specific trade logs, scan metrics, and active position dashboards.
    -   Unified Daily P&L Summary across all segments.
-   **Production Ready**: Automated contract expiry handling, segment-specific holiday detection, and Soft-Simulation mode for off-hours.

## 📁 Project Structure

```text
orbiter/
├── bot/                # Google Sheets logging engine (sheets.py)
├── config/             # Centralized configuration
│   ├── nfo/            # Equity-specific hours & symbols
│   ├── mcx/            # Commodity-specific hours & symbols
│   └── main_config.py  # Global strategy & risk parameters
├── core/
│   ├── broker/         # High-level Broker Wrapper (Exchange Agnostic)
│   └── engine/         # The Trading Brain (State, Evaluator, Executor)
├── data/               # Local JSON mappings & Holiday lists
├── filters/            # Technical Strategy Modules
│   ├── common/         # Agnostic filters (ORB, EMA, Supertrend)
│   ├── sl/             # Stop-Loss logic
│   └── tp/             # Take-Profit & Trailing SL logic
├── logs/               # Segment-specific trade call history
├── utils/              # Market refresh & contract update utilities
└── main.py             # Unified Segment-Aware Application Runner
```

## 🎯 How It Works

1.  **Auto-Detection**: On startup, `main.py` detects the current IST time and loads the appropriate segment (NFO or MCX).
2.  **Scrip Master Initialization**: The `BrokerClient` downloads the official Shoonya masters and resolves current near-month future/option tokens.
3.  **The Loop**:
    -   **Evaluation**: The `Evaluator` calculates technical scores using filters in `filters/common/`.
    -   **Execution**: The `Executor` ranks signals and places either 2-leg Credit Spreads (NFO) or single-leg Futures (MCX).
    -   **Monitoring**: Continuous SL/TP/TSL monitoring with websocket price feeds.
4.  **Logging**: All activity is batch-synced to Google Sheets for real-time portfolio tracking.

## 🛠 Setup & Usage

### 1. Requirements
Ensure you have the Shoonya API library and requirements installed:
```bash
pip install -r orbiter/requirements.txt
```

### 2. Configuration
-   Update `ShoonyaApi-py/cred.yml` with your broker credentials.
-   Update `orbiter/bot/credentials.json` with your Google Cloud Service Account key.

### 3. Initialize Markets
Run the utilities to populate current-month contracts:
```bash
python3 orbiter/utils/nfo/update_futures_config.py
python3 orbiter/utils/mcx/update_mcx_config.py
```

### 4. Run the Bot
```bash
# Start in Live mode
python3 orbiter/main.py

# Start in Simulation mode
python3 orbiter/main.py --simulation
```

## ⚖️ License
Internal private development. FA333160 | 2026.
