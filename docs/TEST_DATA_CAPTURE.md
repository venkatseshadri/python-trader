# Test Data Capture System

> ⚠️ **For complete documentation, see [TEST_DATA_CAPTURE_COMPLETE.md](./TEST_DATA_CAPTURE_COMPLETE.md)**

## Quick Start

| File | Purpose |
|------|---------|
| `orbiter/tests/capture_test_data.py` | One-time script to capture live broker data |
| `orbiter/tests/conftest.py` | Pytest fixtures that load captured data |
| `orbiter/tests/data/` | Directory where captured data is stored |

## Workflow

### Step 1: First Time (Requires Broker Login)

```bash
cd /home/trading_ceo/python-trader

# Run the capture script - requires broker login
python3 orbiter/tests/capture_test_data.py
```

This will:
- Login to broker
- Download scrip masters (NSE, NFO, BFO, MCX)
- Download margin/limits data
- Download sample candle data
- Download current positions
- Save all to `orbiter/tests/data/`

### Step 2: Subsequent Test Runs

```bash
# Run tests - no broker needed
python3 -m pytest orbiter/tests/ -v

# Or run specific test file
python3 -m pytest orbiter/tests/unit/test_captured_data_example.py -v
```

Tests automatically use captured data if available, fallback to mock data otherwise.

## Test Categories

### 1. Tests with Captured Data ✅
- Most unit tests
- Use fixtures from `conftest.py`
- Examples: `scrip_nse`, `captured_margins`, `captured_candles`

### 2. Tests with Strict Mock Data ✅
- Always use hardcoded mocks
- Example: `mock_scrip_data`, `mock_margins`
- No broker or captured data required

### 3. Tests Requiring Live Broker ❌
- Marked with `@pytest.mark.live` or `@pytest.mark.skip`
- Examples:
  - `test_login_success` - needs real credentials
  - `test_actual_margin_calculation` - computes real margins

## Fixtures Available

| Fixture | Description | Data Source |
|---------|-------------|-------------|
| `test_data` | All captured data | captured or empty |
| `scrip_nse` | NSE symbols | captured or mock |
| `scrip_nfo` | NFO options | captured or mock |
| `scrip_bfo` | BFO options | captured or mock |
| `scrip_mcx` | MCX futures | captured or mock |
| `captured_margins` | Margin data | captured or mock |
| `captured_candles` | OHLC data | captured or empty |
| `captured_positions` | Open positions | captured or empty |
| `mock_scrip_data` | Hardcoded mocks | always available |
| `mock_margins` | Hardcoded mocks | always available |
| `mock_candles` | Hardcoded mocks | always available |

## Captured Data Format

### Scrip Master (`scrip_nse.json`)
```json
{
  "12345": {
    "token": "12345",
    "symbol": "RECLTD",
    "tradingsymbol": "RECLTD",
    "exchange": "NSE",
    "lotsize": 1,
    "instrument": "EQ"
  }
}
```

### Margins (`margins.json`)
```json
{
  "cash": 100000,
  "available_balance": 75000,
  "available_margin": 50000,
  "utilized_margin": 25000,
  "capture_time": "2024-01-01T09:15:00"
}
```

### Candles (`candles.json`)
```json
{
  "NSE|12345": {
    "token": "12345",
    "exchange": "NSE",
    "symbol": "RECLTD",
    "candles": [
      {"time": "09:15:00", "into": 100, "inth": 105, "intl": 99, "intc": 103, "v": "1000"}
    ]
  }
}
```

## Updating Captured Data

Run capture periodically to get fresh data:

```bash
python3 orbiter/tests/capture_test_data.py
```

Or force reload in tests:

```python
def test_with_fresh_data(test_data):
    loader = get_test_data_loader()
    loader.load(force=True)  # Reload from files
```

## Migration Guide

Old tests that directly call broker should be updated:

**Before:**
```python
def test_with_broker():
    from orbiter.core.broker.connection import ConnectionManager
    conn = ConnectionManager()
    conn.login()
    data = conn.api.get_scrip_master(exchange='NSE')
```

**After:**
```python
def test_with_captured_data(scrip_nse):
    # Use captured data fixture
    assert len(scrip_nse) > 0
```

## Only 2 Tests Need Live Broker

After full implementation:
1. `test_login_success` - verify credentials work
2. `test_actual_margin_calculation` - compute real margin requirements

These can be skipped in CI or manually run when broker access is available.