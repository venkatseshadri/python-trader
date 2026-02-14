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

## 🛠 Installation Methods

Choose the method that best fits your environment:

### 1. [🐋 Docker (Recommended for Cloud/Desktop)](./install/docker/)
-   Containerized environment with all dependencies pre-configured.
-   Ideal for Railway, DigitalOcean, or stable background execution.
-   [View Docker Setup Guide](./install/docker/README.md)

### 2. [🍓 Raspberry Pi (Low-power Autonomous)](./install/rpi/)
-   Bare-metal installation optimized for 24/7 ARM-based operation.
-   Includes bootstrap scripts for easy deployment.
-   [View Raspberry Pi Guide](./install/rpi/RASPI_SETUP.md)

### 3. [🐍 Manual Virtualenv](./python-trader/README.md)
-   Standard Python setup using `pip` and `.venv`.
-   Best for local development and debugging.

## 📂 Repository Structure

```text
.
├── python-trader/        # Main project (Orbiter + Shoonya API)
│   ├── orbiter/          # The core trading bot engine
│   ├── ShoonyaApi-py/    # Low-level API client library
│   └── ...
├── install/              # Installation Hub
│   ├── docker/           # Docker setup & Compose
│   └── rpi/              # Raspberry Pi setup scripts & docs
├── docs/                 # Documentation Hub (Design & Specs)
└── .venv/                # Python virtual environment
```

---

### 📚 [Documentation Hub](./docs/)
Explore future project roadmaps, technical designs, and the [Modern Cloud Migration Strategy](./docs/CLOUD_MIGRATION.md).
```

## ⚖️ License
Internal private development. 2026.
