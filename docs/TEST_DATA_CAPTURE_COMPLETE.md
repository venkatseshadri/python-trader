# Test Data Capture System - Complete Technical Documentation

## Table of Contents
1. [Overview](#overview)
2. [Architecture](#architecture)
3. [File Structure](#file-structure)
4. [Capture Script Deep Dive](#capture-script-deep-dive)
5. [Conftest Fixtures Deep Dive](#conftest-fixtures-deep-dive)
6. [Data Formats](#data-formats)
7. [Test Categories & Markers](#test-categories--markers)
8. [Migration Guide](#migration-guide)
9. [Troubleshooting](#troubleshooting)
10. [CI/CD Integration](#cicd-integration)
11. [Recovery Procedures](#recovery-procedures)

---

## Overview

### Purpose
The Test Data Capture System enables the orbiter test suite to run **without requiring a live broker connection** after initial data capture. This is critical for:
- **CI/CD pipelines** that cannot authenticate with live brokers
- **Offline development** when market is closed
- **Reproducible tests** using captured real market data
- **Faster test execution** (no network calls)

### How It Works
1. **Capture Phase** (one-time, requires broker): Run `capture_test_data.py` to fetch live data
2. **Storage Phase**: Data saved to `orbiter/tests/data/` as JSON files
3. **Test Phase** (offline): Tests use fixtures that automatically load captured data

### Key Principle
> Tests use **captured real data** when available, **fallback to mock data** when not. Only 2 tests require live broker.

---

## Architecture

### Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           CAPTURE PHASE (One-time)                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐  │
│   │  ConnectionManager │────▶│  get_scrip_master │────▶│  scrip_nse.json  │  │
│   │  (Broker Login)  │     │  (NSE/NFO/BFO)   │     │  scrip_nfo.json  │  │
│   └──────────────────┘     └──────────────────┘     │  scrip_bfo.json  │  │
│                                                      │  scrip_mcx.json  │  │
│                                                      └──────────────────┘  │
│   ┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐  │
│   │  ConnectionManager │────▶│   get_limits    │────▶│  margins.json    │  │
│   └──────────────────┘     └──────────────────┘     └──────────────────┘  │
│                                                                             │
│   ┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐  │
│   │  ConnectionManager │────▶│ get_time_price  │────▶│  candles.json    │  │
│   │                  │     │    _series       │     │  positions.json  │  │
│   └──────────────────┘     └──────────────────┘     └──────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                             TEST PHASE (Offline)                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌──────────────────────────────────────────────────────────────────────┐  │
│   │                     conftest.py - Fixtures                          │  │
│   │  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐    │  │
│   │  │ scrip_nse │  │ scrip_nfo  │  │  captured  │  │  captured  │    │  │
│   │  │  fixture  │  │  fixture   │  │  margins   │  │  candles   │    │  │
│   │  └─────┬─────┘  └─────┬─────┘  └─────┬───────┘  └─────┬───────┘    │  │
│   └────────┼──────────────┼──────────────┼───────────────┼─────────────┘  │
│            │              │              │               │                 │
│            ▼              ▼              ▼               ▼                 │
│   ┌──────────────────────────────────────────────────────────────────────┐  │
│   │              CapturedDataManager (auto-fallback to mocks)           │  │
│   └──────────────────────────────────────────────────────────────────────┘  │
│                                    │                                        │
│                                    ▼                                        │
│   ┌──────────────────────────────────────────────────────────────────────┐  │
│   │                    Test Functions                                   │  │
│   │  test_nse_scrip_data_available()                                    │  │
│   │  test_margin_calculation()                                          │  │
│   │  test_broker_simulation()                                           │  │
│   └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility |
|-----------|----------------|
| `capture_test_data.py` | Fetches live broker data, saves to JSON files |
| `conftest.py` | Provides pytest fixtures with auto-fallback |
| `CapturedDataManager` | Loads/manages captured data files |
| `orbiter/tests/data/` | Storage directory for captured JSON files |

---

## File Structure

```
orbiter/tests/
├── __init__.py                           # Package marker
├── README.md                            # Quick reference
├── capture_test_data.py                 # ⭐ Main capture script
├── conftest.py                          # ⭐ Pytest fixtures
├── data/                                # ⭐ Captured data storage
│   ├── capture_summary.json             # Capture metadata
│   ├── scrip_nse.json                   # NSE equity symbols
│   ├── scrip_nfo.json                   # NSE FnO options
│   ├── scrip_bfo.json                   # BSE FnO options
│   ├── scrip_mcx.json                   # MCX commodities
│   ├── margins.json                     # Account margin data
│   ├── candles.json                     # Historical OHLCV data
│   ├── positions.json                   # Current positions
│   └── archive/                         # Old captures (backup)
├── brokers/                             # Broker-specific tests
│   ├── test_shoonya_api.py
│   ├── test_broker_executor.py
│   └── test_connection_and_debrief.py
├── flow/                                # Integration tests
├── integration/                         # Full system tests
└── unit/                                # Unit tests
    ├── test_captured_data_example.py    # Example usage
    └── ...                              # 50+ other test files
```

---

## Capture Script Deep Dive

### Script Location
```
/home/trading_ceo/python-trader/orbiter/tests/capture_test_data.py
```

### Purpose
One-time script that authenticates with the broker and downloads essential market data for testing.

### Execution Requirements
1. **Broker credentials** in `orbiter/cred.yml` or `ShoonyaApi-py/cred.yml`
2. **Live market connection** (may not work on holidays/weekends)
3. **Network access** to broker API endpoints

### Command Line Options

```bash
python3 orbiter/tests/capture_test_data.py [OPTIONS]

Options:
  --output-dir PATH    Output directory (default: orbiter/tests/data)
  --exchanges EXCH     Comma-separated exchanges (default: NSE,NFO,BFO,MCX)
```

### What Gets Captured

| Data Type | API Call | Exchange | Records | File |
|-----------|----------|----------|---------|------|
| Scrip Master | `get_scrip_master()` | NSE | ~2000 | `scrip_nse.json` |
| Scrip Master | `get_scrip_master()` | NFO | ~50000 | `scrip_nfo.json` |
| Scrip Master | `get_scrip_master()` | BFO | ~5000 | `scrip_bfo.json` |
| Scrip Master | `get_scrip_master()` | MCX | ~100 | `scrip_mcx.json` |
| Margins | `get_limits()` | All | 1 | `margins.json` |
| Candles | `get_time_price_series()` | NSE | 20 symbols | `candles.json` |
| Positions | `get_positions()` | All | N | `positions.json` |

### Code Flow

```python
# 1. Initialize broker connection
conn = get_broker_client()  # ConnectionManager.login()

# 2. Capture scrip masters for each exchange
for exchange in ['NSE', 'NFO', 'BFO', 'MCX']:
    data = capture_scrip_master(conn, exchange, output_dir)
    # Result: token-indexed dict like {'12345': {'symbol': 'RECLTD', ...}}

# 3. Capture margin data
margins = capture_margins(conn, output_dir)
# Result: {'cash': 100000, 'available_margin': 50000, ...}

# 4. Capture sample candles (last 60 mins, 5-min intervals)
capture_candles(conn, sample_symbols, output_dir)
# Result: {'NSE|12345': {'candles': [...]}}

# 5. Capture current positions
positions = capture_positions(conn, output_dir)
# Result: {'positions': [...]}

# 6. Save summary
save_capture_summary(output_dir, summary)
```

### Sample Output

```
2024-01-15 09:20:00 - INFO - 🔐 Initializing broker connection...
2024-01-15 09:20:01 - INFO - ✅ Logged in successfully
2024-01-15 09:20:01 - INFO - 📥 Capturing scrip master for NSE...
2024-01-15 09:20:02 - INFO -    Got 2156 symbols for NSE
2024-01-15 09:20:02 - INFO -    💾 Saved to .../scrip_nse.json
2024-01-15 09:20:02 - INFO - 📥 Capturing scrip master for NFO...
2024-01-15 09:20:05 - INFO -    Got 48234 symbols for NFO
...
2024-01-15 09:21:30 - INFO - ==================================================
2024-01-15 09:21:30 - INFO - ✅ DATA CAPTURE COMPLETE!
2024-01-15 09:21:30 - INFO -    Scrip masters: {'NSE': 2156, 'NFO': 48234, 'BFO': 5234, 'MCX': 87}
2024-01-15 09:21:30 - INFO -    Margins: Yes
2024-01-15 09:21:30 - INFO -    Positions: 0
2024-01-15 09:21:30 - INFO - ==================================================
```

---

## Conftest Fixtures Deep Dive

### File Location
```
/home/trading_ceo/python-trader/orbiter/tests/conftest.py
```

### Purpose
Provides pytest fixtures that:
1. Load captured data when available
2. Fall back to mock data when not available
3. Enable tests to run without broker connection

### How Fixtures Work

#### Fixture Loading Chain
```
test function
    │
    ▼
@pytest.fixture
    │
    ▼
test_data (session-scoped)
    │
    ▼
CapturedDataManager.load()
    │
    ├───▶ Load from JSON files (if exists)
    │
    └───▶ Return empty dict (if not exists)
    │
    ▼
Return data OR fallback to mock
```

#### Key Classes

**CapturedDataManager**
```python
class CapturedDataManager:
    """Manages loading of captured test data."""
    
    def __init__(self):
        self.data = {}
        self.data_dir = 'orbiter/tests/data'
        self._loaded = False
    
    def load(self, force: bool = False) -> dict:
        """Load all captured data files."""
        if self._loaded and not force:
            return self.data
        
        # Check if capture_summary.json exists
        if not os.path.exists(os.path.join(self.data_dir, 'capture_summary.json')):
            logger.info("⚠️ No captured data found - tests will use mocks")
            return {}
        
        # Load each file
        for filename in ['scrip_nse.json', 'scrip_nfo.json', ...]:
            # ... load JSON ...
        
        return self.data
```

### Available Fixtures

| Fixture | Scope | Data Source | Use Case |
|---------|-------|--------------|----------|
| `test_data` | session | captured or {} | Raw access to all data |
| `has_captured_data` | session | boolean | Check if captured data exists |
| `scrip_nse` | session | captured → mock | NSE equity symbols |
| `scrip_nfo` | session | captured → mock | NSE FnO options |
| `scrip_bfo` | session | captured or {} | BSE FnO options |
| `scrip_mcx` | session | captured or {} | MCX commodities |
| `captured_margins` | session | captured → mock | Account margin data |
| `captured_candles` | session | captured or {} | OHLCV data |
| `captured_positions` | session | captured or {} | Open positions |
| `mock_scrip_data` | function | always mock | Strict mock (no fallback) |
| `mock_margins` | function | always mock | Strict mock (no fallback) |
| `mock_candles` | function | always mock | Strict mock (no fallback) |
| `mock_positions` | function | always mock | Strict mock (no fallback) |

### Using Fixtures in Tests

#### Example 1: Using Captured Data with Fallback
```python
def test_nse_scrip_available(self, scrip_nse):
    """NSE data - uses captured if available, mock if not."""
    assert len(scrip_nse) > 0  # Always passes
    # If captured: real ~2000 symbols
    # If not: mock 1 symbol
```

#### Example 2: Using Strict Mocks
```python
def test_exact_behavior(self, mock_scrip_data):
    """Always uses hardcoded mock - no fallback."""
    assert mock_scrip_data['12345']['symbol'] == 'RECLTD'
    # Guaranteed consistent across runs
```

#### Example 3: Check if Captured Data Exists
```python
def test_conditional_logic(self, has_captured_data):
    """Branch based on whether captured data exists."""
    if has_captured_data:
        # Use real data path
        do_something()
    else:
        # Use mock path
        do_other_thing()
```

---

## Data Formats

### Scrip Master (scrip_nse.json)

**Structure:** Token-indexed dictionary
```json
{
  "12345": {
    "token": "12345",
    "symbol": "RECLTD",
    "tradingsymbol": "RECLTD",
    "exchange": "NSE",
    "lotsize": 1,
    "instrument": "EQ"
  },
  "123456": {
    "token": "123456",
    "symbol": "ZYDUSLIFE",
    "tradingsymbol": "ZYDUSLIFE26MAY26P1280",
    "exchange": "NFO",
    "lotsize": 900,
    "instrument": "OPTSTK",
    "option_type": "PE",
    "strike_price": 1280,
    "expiry": "26-MAY-2026"
  }
}
```

**Field Meanings:**
| Field | Type | Description |
|-------|------|-------------|
| `token` | string | Unique broker token ID |
| `symbol` | string | Short symbol (e.g., "RECLTD") |
| `tradingsymbol` | string | Full trading symbol (e.g., "RECLTD") |
| `exchange` | string | Exchange (NSE/NFO/BFO/MCX) |
| `lotsize` | int | Minimum lot size |
| `instrument` | string | Instrument type (EQ/OPTSTK/FUTSTK/etc.) |
| `option_type` | string | Option type (CE/PE) - options only |
| `strike_price` | int | Strike price - options only |
| `expiry` | string | Expiry date - derivatives only |

### Margins (margins.json)

**Structure:**
```json
{
  "cash": 100000,
  "available_balance": 75000,
  "available_margin": 50000,
  "utilized_margin": 25000,
  "available_margin_sqr": 45000,
  "segment_limits": [
    {"exchange": "NSE", "margin": 25000},
    {"exchange": "NFO", "margin": 20000}
  ],
  "capture_time": "2024-01-15T09:15:00.000000"
}
```

**Field Meanings:**
| Field | Type | Description |
|-------|------|-------------|
| `cash` | float | Total cash in account |
| `available_balance` | float | Available balance for trading |
| `available_margin` | float | Available margin for FnO |
| `utilized_margin` | float | Currently used margin |
| `available_margin_sqr` | float | Margin for MIS/BO/CO products |
| `segment_limits` | array | Per-exchange limits |
| `capture_time` | string | ISO timestamp of capture |

### Candles (candles.json)

**Structure:** Exchange|Token-keyed dictionary
```json
{
  "NSE|12345": {
    "token": "12345",
    "exchange": "NSE",
    "symbol": "RECLTD",
    "candles": [
      {
        "time": "2024-01-15 09:15:00",
        "into": 100.5,
        "inth": 102.3,
        "intl": 99.8,
        "intc": 101.2,
        "v": "1500000"
      }
    ],
    "count": 50
  }
}
```

**Candle Field Meanings:**
| Field | Description |
|-------|-------------|
| `time` | Candle timestamp |
| `into` | Open price |
| `inth` | High price |
| `intl` | Low price |
| `intc` | Close price |
| `v` | Volume |

### Positions (positions.json)

**Structure:**
```json
{
  "positions": [
    {
      "tsym": "RECLTD",
      "token": "12345",
      "exch": "NSE",
      "netqty": "100",
      "rpnl": "1500.00",
      "urpnl": "200.00"
    }
  ],
  "count": 1
}
```

### Capture Summary (capture_summary.json)

**Structure:**
```json
{
  "capture_time": "2024-01-15T09:15:00.000000",
  "exchanges": {
    "NSE": 2156,
    "NFO": 48234,
    "BFO": 5234,
    "MCX": 87
  },
  "margins_available": true,
  "positions_count": 0
}
```

---

## Test Categories & Markers

### Test Categories

| Category | Count | Requires Broker | Can Run Offline |
|----------|-------|-----------------|-----------------|
| Unit Tests | ~100 | No | Yes |
| Broker Tests | ~10 | Yes | No |
| Integration Tests | ~5 | Yes | No |
| Captured Data Tests | ~5 | No | Yes |

### Pytest Markers

Defined in `conftest.py`:
```python
def pytest_configure(config):
    config.addinivalue_line("markers", "broker: tests that require live broker connection")
    config.addinivalue_line("markers", "data: tests that require real market data files")
    config.addinivalue_line("markers", "integration: tests that require full system integration")
    config.addinivalue_line("markers", "captured: tests that prefer captured data over live")
    config.addinivalue_line("markers", "live: tests that require live broker connection")
```

### Using Markers

```python
# Skip test unless broker is available
@pytest.mark.broker
@pytest.mark.skip(reason="Requires live broker")
def test_login():
    ...

# Only run when captured data exists
@pytest.mark.captured
def test_with_real_data():
    ...

# Force live broker test
@pytest.mark.live
def test_actual_margin():
    ...
```

### Running Tests by Marker

```bash
# Run only captured data tests
pytest orbiter/tests/ -m captured -v

# Skip broker tests
pytest orbiter/tests/ -m "not broker" -v

# Run only unit tests (no broker needed)
pytest orbiter/tests/unit/ -v
```

---

## Migration Guide

### Converting Old Tests

**Before: Direct Broker Call**
```python
def test_with_broker():
    from orbiter.core.broker.connection import ConnectionManager
    
    conn = ConnectionManager()
    conn.login()
    data = conn.api.get_scrip_master(exchange='NSE')
    
    assert len(data) > 0
    conn.close()
```

**After: Using Fixture**
```python
def test_with_captured_data(scrip_nse):
    """Uses captured data if available, mock if not."""
    assert len(scrip_nse) > 0
    
    # Use data...
    token = list(scrip_nse.keys())[0]
    symbol = scrip_nse[token]['symbol']
```

**After: Strict Mock (for deterministic tests)**
```python
def test_with_strict_mock(mock_scrip_data):
    """Always uses hardcoded mock - no network/fallback."""
    assert '12345' in mock_scrip_data
    assert mock_scrip_data['12345']['symbol'] == 'RECLTD'
```

### When to Use What

| Scenario | Fixture | Reason |
|----------|---------|--------|
| Testing real data parsing | `scrip_nse` | Uses real ~2000 symbols |
| Testing edge cases | `mock_scrip_data` | Known, controlled input |
| Testing margin logic | `captured_margins` | Uses real margin values |
| Testing error handling | `mock_margins` | Controlled failure scenarios |
| Testing candle indicators | `captured_candles` | Real OHLC patterns |

---

## Troubleshooting

### Issue: "No captured data found - tests will use mocks"

**Cause:** `capture_summary.json` doesn't exist

**Solution:**
```bash
# Run capture script (requires broker login)
cd /home/trading_ceo/python-trader
python3 orbiter/tests/capture_test_data.py
```

### Issue: "Failed to capture NFO: ..."

**Cause:** Market closed or API issue

**Solution:**
```bash
# Try on a trading day during market hours
# Or capture only available exchanges
python3 orbiter/tests/capture_test_data.py --exchanges NSE
```

### Issue: Test passes locally but fails in CI

**Cause:** CI doesn't have captured data files

**Solution:**
1. Capture data locally
2. Commit captured data files to repo
3. OR use artifacts/caching in CI

### Issue: Mock data not being used as fallback

**Cause:** Fixture returning empty dict

**Solution:** Check fixture code - ensure fallback returns mock:
```python
@pytest.fixture
def scrip_nse(test_data):
    data = test_data.get('scrip_nse', {})
    if not data:
        # MUST return mock here!
        return {
            '12345': {
                'token': '12345',
                'symbol': 'RECLTD',
                ...
            }
        }
    return data
```

### Issue: Broker login fails

**Cause:** Invalid credentials or TOTP issue

**Solution:**
```bash
# Check credentials file
cat /home/trading_ceo/python-trader/ShoonyaApi-py/cred.yml

# Verify TOTP is working
# Manual TOTP: https://totp.dheysonalves.com/
```

---

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Python
      uses: actions/setup-python@v5
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install pytest
    
    - name: Check for captured data
      run: |
        if [ ! -f orbiter/tests/data/capture_summary.json ]; then
          echo "⚠️ No captured data - tests will use mocks"
        fi
    
    - name: Run tests
      run: |
        python -m pytest orbiter/tests/ -v --tb=short
    
    - name: Upload captured data (if exists)
      if: github.event_name == 'schedule'
      uses: actions/upload-artifact@v4
      with:
        name: captured-test-data
        path: orbiter/tests/data/
```

### Running Without Captured Data

```bash
# Skip all broker-dependent tests
pytest orbiter/tests/ -m "not broker" -v

# Only run unit tests
pytest orbiter/tests/unit/ -v

# With verbose output
pytest orbiter/tests/ -v -ra
```

---

## Recovery Procedures

### Scenario 1: Lost All Memory - Recreate from Scratch

**If you forget everything about this system:**

1. **Find the capture script:**
   ```bash
   find /home/trading_ceo/python-trader -name "capture_test_data.py"
   ```

2. **Run it with broker credentials:**
   ```bash
   cd /home/trading_ceo/python-trader
   python3 orbiter/tests/capture_test_data.py
   ```

3. **Run tests:**
   ```bash
   python3 -m pytest orbiter/tests/ -v
   ```

### Scenario 2: Corrupted Data Files

**If JSON files are corrupted:**

1. **Delete corrupted files:**
   ```bash
   rm orbiter/tests/data/*.json
   ```

2. **Recapture:**
   ```bash
   python3 orbiter/tests/capture_test_data.py
   ```

### Scenario 3: Want Fresh Captured Data

**If data is stale (old expiry dates, etc.):**

1. **Backup old data:**
   ```bash
   mkdir -p orbiter/tests/data/archive
   mv orbiter/tests/data/scrip_*.json orbiter/tests/data/archive/
   mv orbiter/tests/data/margins.json orbiter/tests/data/archive/
   ```

2. **Recapture:**
   ```bash
   python3 orbiter/tests/capture_test_data.py
   ```

### Scenario 4: Add New Data Type

**If you need to capture new data (e.g., order history):**

1. **Add capture function in `capture_test_data.py`:**
   ```python
   def capture_order_history(conn, output_dir: str):
       ret = conn.api.get_order_history()
       # Save to order_history.json
   ```

2. **Add fixture in `conftest.py`:**
   ```python
   @pytest.fixture
   def captured_order_history(test_data):
       return test_data.get('order_history', {})
   ```

3. **Use in tests:**
   ```python
   def test_order_history(captured_order_history):
       ...
   ```

---

## Appendix: Complete File Listings

### capture_test_data.py Imports
```python
import os, sys, json, argparse, logging
from datetime import datetime, timedelta
from typing import Dict, Any, List
```

### conftest.py Imports
```python
import os, sys, json, logging, pytest
```

### Key Paths
| Purpose | Path |
|---------|------|
| Project Root | `/home/trading_ceo/python-trader` |
| Capture Script | `/home/trading_ceo/python-trader/orbiter/tests/capture_test_data.py` |
| Fixtures | `/home/trading_ceo/python-trader/orbiter/tests/conftest.py` |
| Data Directory | `/home/trading_ceo/python-trader/orbiter/tests/data/` |
| Credentials | `/home/trading_ceo/python-trader/ShoonyaApi-py/cred.yml` |

---

## Quick Reference Card

```bash
# ===== ONE-TIME SETUP =====

# 1. Capture live data (requires broker)
cd /home/trading_ceo/python-trader
python3 orbiter/tests/capture_test_data.py

# ===== RUN TESTS =====

# All tests (uses captured data if available)
python3 -m pytest orbiter/tests/ -v

# Only unit tests (fastest, no broker needed)
python3 -m pytest orbiter/tests/unit/ -v

# With captured data only
python3 -m pytest orbiter/tests/ -m captured -v

# Skip broker tests
python3 -m pytest orbiter/tests/ -m "not broker" -v

# ===== UPDATE CAPTURED DATA =====

# Refresh data (new capture)
python3 orbiter/tests/capture_test_data.py

# Or specific exchanges
python3 orbiter/tests/capture_test_data.py --exchanges NSE,NFO
```

---

*Last Updated: 2024-01-15*
*Version: 1.0*
*Maintainer: Kubera (AI Trading Assistant)*
