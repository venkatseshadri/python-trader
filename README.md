# Python Trading Ecosystem

> **⚠️ NOTE (Apr 20, 2026):** Orbiter is PAUSED. Active strategies are **Varaha** and **Matsaya** using **dual broker (Shoonya + Flattrade)**. See [BROKER_ASSIGNMENT.md](./BROKER_ASSIGNMENT.md) for details.

A comprehensive suite of tools and frameworks for automated trading in the Indian stock and commodity markets using the **Shoonya (Finvasia) API**.

## 🚀 Active Projects

### 1. 🐢 [Kurma](./kurma/) — MCX Evening Commodities Trading
**Automated intraday trading bot for MCX futures** (5:00 PM - 11:20 PM IST)
- **Strategy:** Dynamic instrument selection + momentum entry + partial TP + trailing stop
- **Capital:** Reuses ₹4,00,000 released by Varaha at 3:10 PM
- **Target:** ₹1,000-₹1,500 daily profit from Crude Oil, Gold, Silver, Natural Gas
- **Status:** ✅ Production Ready
- **Brokers:** Shoonya (OAuth2, ✅ working) | Flattrade (blocked - MCX not enabled)
- **[Quick Start →](./kurma/README.md) | [Architecture →](./kurma/CLAUDE.md) | [Broker Setup →](./kurma/BROKER_AUTHENTICATION_GUIDE.md)**

### 2. 🐢 [Varaha](./VARAHA_GUIDE.md) — NFO/BFO Index Futures Trading
**Systematic index trading bot for NIFTY and SENSEX** (9:20 AM - 3:05 PM IST)
- **Strategy:** Trend-following with 3-tranche exits (50/25/25 partial TP + TSL)
- **Capital:** ₹4,00,000 margin from account, releases at 3:05 PM for Kurma
- **Target:** ₹3,000-₹5,000 daily profit using NFO/BFO instruments
- **Status:** ✅ Production Ready
- **Brokers:** Shoonya (OAuth2, ✅ working) | Flattrade (alternative)
- **[Complete Guide →](./VARAHA_GUIDE.md) | [Broker API Testing →](./BROKER_API_TESTING_GUIDE.md)**

### 3. [ShoonyaApi-py](./ShoonyaApi-py/)
A robust, low-level Python wrapper for the Shoonya REST and WebSocket APIs.
- Comprehensive coverage of order management, market data, and historical series.
- Integrated SPAN margin and Option Greek calculators.
- Used as the backbone for Kurma and Varaha trading engines.

### 4. [Orbiter](./orbiter/) — Comprehensive Trading Framework (PAUSED)
The legacy trading framework featuring technical analysis filters and modular design.
- **Status:** ⏸️ Paused - Active development shifted to Kurma/Varaha
- Contains valuable test utilities for broker API validation

## 🧪 Testing & Broker Validation

Before trading with Kurma or Varaha, verify broker connectivity:

### Quick Verification (5 minutes)
```bash
# 1. Test broker configuration
python3 -m pytest ShoonyaApi-py/tests/test_broker_config.py -v

# 2. Refresh OAuth token (if expired)
cd Shoonya_oAuthAPI-py
python3 GetAuthcode.py

# 3. Test OHLC data (MCX for Kurma, NFO/BFO for Varaha)
python3 << 'EOF'
from api_helper import NorenApiPy
import yaml

with open('Shoonya_oAuthAPI-py/cred.yml') as f:
    cred = yaml.safe_load(f)

api = NorenApiPy()
if api.set_session(userid=cred['UID'], accesstoken=cred['Access_token']):
    limits = api.get_limits()
    print(f"✅ Authenticated. Available margin: ₹{float(limits.get('cash')):,.0f}")
else:
    print("❌ Session failed - refresh token")
EOF
```

### Comprehensive Testing
See **[BROKER_API_TESTING_GUIDE.md](./BROKER_API_TESTING_GUIDE.md)** for:
- All 15+ test files (configuration, tokens, OHLC, margin, connectivity)
- How to run each test
- Expected outputs
- Troubleshooting common failures

### Test Coverage
| Test | File | Purpose |
|------|------|---------|
| Broker Config | `test_broker_config.py` | Verify endpoints for Shoonya/Flattrade |
| Token Generation | `GetAuthcode.py` | OAuth2 automation with Selenium |
| OHLC Data (MCX) | `test_tpSeries.py` | Kurma's commodity data feed |
| OHLC Data (NFO/BFO) | `test_tpSeries.py` | Varaha's index data feed |
| Margin API | `test_margin.py` | Position sizing validation |
| Authentication | `test_connection_and_debrief.py` | Login/logout flow |

---

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
