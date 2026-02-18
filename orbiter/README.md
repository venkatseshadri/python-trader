# ORBITER

[![Status][status-badge]][status-link] [![Python][python-badge]][python-link] [![License][license-badge]][license-link]

**ORBITER v3.2.0-20260218-ce903b5** - Unified Segment Multi-Market Trader

Scans NIFTY/MCX symbols for ORB breakouts, ranks by momentum strength, and executes Option Credit Spreads with margin-efficient leg sequencing.

## 🚀 Features

- **Multi-Market Support** → Automatic NFO/MCX segment switching
- **Modular Engine v3** → Decoupled Evaluator, Executor, and State management
- **Credit Spreads** → Sell ATM / Buy Hedge for margin benefit (auto-sequenced)
- **Shoonya API** → Production-grade REST + Websocket integration
- **Live SL/Target Monitoring** → Portfolio-wide and individual position management
- **Simulation Mode** → Full dry-run with real market data
- **Versioning** → Integrated version logging to ensure environment parity

## 📁 Architecture

orbiter/
├── config/         # Multi-segment + strategy params
├── core/           
│   ├── broker/     # Modular Broker Client (New v3)
│   ├── engine/     # Evaluator, Executor, State
├── bot/            # Google Sheets + Telegram Bot (Planned)
├── filters/        # Signal & Exit filters (v1-v8)
├── data/           # Symbols, Masters, Margin Caches
└── main.py         # Entry point (Generic runner)

## 🎯 How It Works

1. **Auto-Detect Segment**: Switches between NFO (Day) and MCX (Evening) based on time.
2. **Scan Universe**: Pulls ORB (9:15-9:30) high/low and LTP.
3. **Rank Signals**: Sorts by breakout distance (Top N).
4. **Leg Sequencing**: For Credit Spreads, buys the Hedge first to unlock margin benefit, then sells the ATM.
5. **Live Monitoring**: Websocket feed monitors premium for SL/TP hits.

## 🛠 Quick Start

### Development (Mac/Local)
```bash
# 1. Setup
git clone <repo>
cd python-trader

# 2. Run simulation
python orbiter/main.py --simulation

# 3. Go live
python orbiter/main.py
```

### Production (Raspberry Pi Daemon)
For 24/7 operation with automatic crash recovery and session switching (NFO -> MCX):

1. **Install Service**:
   ```bash
   sudo cp install/rpi/orbiter.service /etc/systemd/system/
   cp install/rpi/orbiter.env /home/pi/python/
   sudo systemctl daemon-reload
   sudo systemctl enable orbiter
   ```

2. **Configure Mode**:
   Edit `/home/pi/python/orbiter.env` to toggle simulation:
   - `ORBITER_FLAGS=""` (Live Mode)
   - `ORBITER_FLAGS="--simulation"` (Simulation Mode)

3. **Control**:
   ```bash
   sudo systemctl start orbiter    # Start
   sudo systemctl stop orbiter     # Stop
   sudo systemctl restart orbiter  # Restart (Apply .env changes)
   sudo systemctl status orbiter   # Check Health
   ```

## 📋 Monitoring & Logs

Orbiter generates comprehensive logs to handle background sessions (e.g., `screen` or `systemd`):

- **System Logs**: `logs/system/orbiter_YYYYMMDD_HHMM.log` (Captures everything: prints, errors, crashes).
- **Trade Logs**: `logs/nfo/trade_calls.log` (Specific to execution calls).
- **Service Logs**: `sudo journalctl -u orbiter -f` (Linux system-level logs).

## 🛡️ Release & Integrity

Before pushing changes, always run the release script to sync versions and checksums:
```bash
./release.sh
```
This updates `version.txt`, `main.py`, and regenerates `checksums.txt` for environment parity.

Version 3.6.3-20260218-0c972a7 - Feb 2026
