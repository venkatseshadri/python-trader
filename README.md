# Python Trading Ecosystem

A comprehensive suite of tools and frameworks for automated trading in the Indian stock and commodity markets using the **Shoonya (Finvasia) API**.

## 🚀 Projects in this Repository

### 1. [python-trader](./python-trader/)
The flagship trading application, featuring the **ORBITER v3.0** framework.
- **Dual-Session**: Trades Equity Derivatives (NFO) during the day and Commodities (MCX) in the evening.
- **Modular Engine**: Decoupled technical filters, risk management, and execution logic.
- **Cloud Sync**: Real-time logging and dashboarding via Google Sheets.
- **Raspberry Pi Ready**: Optimized for low-power, 24/7 autonomous operation.

### 2. [ShoonyaApi-py](./python-trader/ShoonyaApi-py/)
A robust, low-level Python wrapper for the Shoonya REST and WebSocket APIs.
- Comprehensive coverage of order management, market data, and historical series.
- Integrated SPAN margin and Option Greek calculators.
- Used as the backbone for the Orbiter trading engine.

## 🛠 Quick Start

1. **Environment Setup**:
   ```bash
   # Create and activate virtual environment
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r python-trader/orbiter/requirements.txt
   ```

2. **Configuration**:
   - Update `python-trader/ShoonyaApi-py/cred.yml` with your API credentials.
   - Update `python-trader/orbiter/bot/credentials.json` for Google Sheets integration.

3. **Execution**:
   ```bash
   cd python-trader/orbiter
   python3 main.py --simulation
   ```

## 📂 Repository Structure

```text
.
├── python-trader/        # Main project (Orbiter + Shoonya API)
│   ├── orbiter/          # The core trading bot engine
│   ├── ShoonyaApi-py/    # Low-level API client library
│   ├── scripts/          # Deployment and run scripts
│   └── ...
├── docs/                 # Documentation Hub
│   ├── setup/            # Setup guides (RPi, Cloud, etc.)
│   └── ...
└── .venv/                # Python virtual environment
```

---

### 📚 [Documentation Hub](./docs/)
Explore future project roadmaps, technical designs, and the [Modern Cloud Migration Strategy](./docs/CLOUD_MIGRATION.md).
```

## ⚖️ License
Internal private development. 2026.
