# 🧪 Testing Guide

ORBITER v3.0 uses a rigorous testing strategy to ensure that changes to the core engine or cloud migration do not break existing trading strategies.

## 🛠 Framework
- **Primary Tool**: `pytest`
- **Plugins**: `pytest-mock` (for isolating API calls)
- **Data Source**: `tests/data/scenario_data.json` (actual market events)

## 📂 Directory Structure
```text
tests/
├── data/
│   ├── archive/          # Historical CSV data (zipped)
│   └── scenario_data.json # Parametrized market scenarios
├── integration/
│   └── test_shoonya_api.py # Real API connectivity tests
└── unit/
    ├── test_master_base.py # Scrip Master & Utility tests
    └── test_scenarios.py   # Strategy & Filter logic tests
```

## 🚀 How to Run Tests

### 1. Unit Tests (Fast, no API required)
```bash
export PYTHONPATH=$PYTHONPATH:$(pwd):$(pwd)/../ShoonyaApi-py
pytest tests/unit
```

### 2. Integration Tests (Requires valid `cred.yml`)
```bash
pytest tests/integration
```

## 📊 Market Scenario Testing (Data-Driven)
The core of our strategy validation lies in `test_scenarios.py`. It reads `scenario_data.json`, which contains actual numbers from NIFTY 50 SPOT archives.

### Current Test Coverage:
1.  **Bullish ORB Breakout**: Validates that `f1_orb.py` correctly calculates scores when the 15-minute high is breached.
2.  **Stop Loss Hit**: Confirms that the hard exit logic triggers correctly on a percentage-based pullback.
3.  **Trailing Stop Loss**: Ensures the bot "Holds" or "Exits" correctly based on the relationship between current LTP and the trailed SL level.

## 📝 Adding New Scenarios
To add a new test case:
1. Extract the OHLC data from the archive ZIP.
2. Add a new entry to the `scenarios` list in `scenario_data.json`.
3. Run `pytest` to confirm the engine behaves as expected.
