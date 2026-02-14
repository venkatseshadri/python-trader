# Python Trader

An automated trading ecosystem focused on the Indian markets. This repository contains the high-level trading engine and the supporting API wrappers.

## 🌟 Component Overview

### [ORBITER v3.0](./orbiter/)
The primary trading framework. It is designed for **Multi-Market, Multi-Segment** execution.
- **Morning (NFO)**: Scans Nifty 50 stocks for high-probability Credit Spreads.
- **Evening (MCX)**: Trades Commodity Futures with momentum-based filters.
- **Risk Control**: Integrated Stop-Loss, Take-Profit, and Trailing SL logic.

### [ShoonyaApi-py](./ShoonyaApi-py/)
The underlying communication layer. A customized Python client for the Shoonya API that handles:
- REST authentication and session management.
- Multi-threaded WebSocket feeds for real-time price updates.
- Scrip master downloads and local caching.

## 🚀 Getting Started

If you are setting this up for the first time, follow these steps:

1. **Install Dependencies**:
   ```bash
   ./scripts/install.sh
   ```

2. **Configure Credentials**:
   Edit `ShoonyaApi-py/cred.yml` and add your broker `uid`, `pwd`, `factor2`, `vc`, `app_key`, and `imei`.

3. **Initialize Market Data**:
   ```bash
   python3 orbiter/utils/nfo/update_futures_config.py
   python3 orbiter/utils/mcx/update_mcx_config.py
   ```

4. **Run the Bot**:
   ```bash
   ./scripts/run.sh
   ```

## 🖥 Deployment

For instructions on how to deploy this on a **Raspberry Pi** for 24/7 trading, see the [RASPI_SETUP.md](./RASPI_SETUP.md) guide.

## 📊 Monitoring

The bot logs all activities to **Google Sheets**. Ensure your service account key is placed in `orbiter/bot/credentials.json` and the Spreadsheet ID is configured in `orbiter/config/main_config.py`.

---
Internal Development | 2026.
