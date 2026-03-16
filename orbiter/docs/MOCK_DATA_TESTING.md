# Mock Data Testing for Orbiter

This document describes the mock data feature that allows testing Orbiter outside market hours using pre-recorded historical data.

## Overview

The mock data feature replaces the real broker connection (websocket + REST API) with a mock broker that replays pre-recorded candle data. This enables:

- **Off-hours testing**: Test Orbiter's strategy logic outside market hours
- **Historical replay**: Replay market conditions from captured data
- **CI/CD testing**: Run automated tests without real API connections
- **Debugging**: Isolate issues by controlling the data source

## Quick Start

### Basic Usage

```bash
# Run with mock data (requires market hours simulation for full testing)
ORBITER_SIMULATE_MARKET_HOURS=true python -m orbiter.main --mock_data=true --strategyCode=n1

# Or with paper trade (recommended for testing)
ORBITER_SIMULATE_MARKET_HOURS=true python -m orbiter.main --paper_trade=true --mock_data=true --strategyCode=n1
```

### With Custom Data File

```bash
ORBITER_SIMULATE_MARKET_HOURS=true python -m orbiter.main \
  --paper_trade=true \
  --mock_data=true \
  --mock_data_file=orbiter/test_data/nifty_full.json \
  --strategyCode=n1
```

## Command Line Arguments

| Argument | Description | Example |
|----------|-------------|---------|
| `--mock_data=true` | Enable mock broker (replaces real websocket/REST) | `--mock_data=true` |
| `--mock_data_file=/path/to/data.json` | Path to custom JSON data file | `--mock_data_file=orbiter/test_data/nifty_full.json` |

### Alternative Syntax

The argument parser supports multiple formats:
- `--mock_data=true` or `--mock_data=true`
- `--mockData=true` (camelCase)

## Environment Variables

| Variable | Description | Values |
|----------|-------------|--------|
| `ORBITER_SIMULATE_MARKET_HOURS` | Force market open state | `true` or `false` |
| `ORBITER_MOCK_DATA_FILE` | Override data file path | Full path to JSON |

### Example with Environment Variable

```bash
export ORBITER_MOCK_DATA_FILE=/home/trading_ceo/python-trader/orbiter/test_data/nifty_full.json
export ORBITER_SIMULATE_MARKET_HOURS=true
python -m orbiter.main --paper_trade=true --mock_data=true --strategyCode=n1
```

## Data File Format

The mock broker expects JSON files with candle data in the following format:

```json
{
  "NSE_NIFTY": {
    "symbol": "NIFTY",
    "token": "26000",
    "exchange": "NSE",
    "candles": [
      {
        "time": "2026-01-23 09:15:00",
        "into": "25058.1",
        "inth": "25064.5",
        "intl": "25057.25",
        "intc": "25062.65",
        "intv": "0",
        "oi": "0"
      },
      ...
    ]
  },
  "NSE_RELIANCE": {
    "symbol": "RELIANCE",
    "token": "2885", 
    "exchange": "NSE",
    "candles": [...]
  }
}
```

### Field Descriptions

| Field | Description |
|-------|-------------|
| `symbol` | Trading symbol (e.g., "NIFTY", "RELIANCE") |
| `token` | Exchange token (numeric or string) |
| `exchange` | Exchange code (NSE, BFO, MCX) |
| `candles` | Array of OHLCV candles |
| `candles[].time` | Timestamp (YYYY-MM-DD HH:MM:SS) |
| `candles[].into` | Open price |
| `candles[].inth` | High price |
| `candles[].intl` | Low price |
| `candles[].intc` | Close price |
| `candles[].intv` | Volume |
| `candles[].oi` | Open Interest |

## Included Test Data

The repository includes sample data files in `orbiter/test_data/`:

| File | Description | Instruments | Candles |
|------|-------------|-------------|---------|
| `nfo_data.json` | NSE F&O sample | 8 | 75 |
| `bfo_data.json` | BSE F&O sample | 1 | 75 |
| `mcx_data.json` | MCX commodities | 4 | 110+ |
| `nifty_full.json` | Nifty 50 stocks | 105 | 100 each |

### Note on Test Data

The included `nfo_data.json` was captured during a limited test with only 8 instruments. For comprehensive testing with all 53 NFO instruments, you need to either:

1. **Capture your own data** during market hours
2. **Use historical data** (see Data Conversion section)

## Converting Historical Data

Use the included converter to transform CSV intraday data to mock broker format:

### Usage

```bash
python orbiter/test_data/convert_nifty_data.py \
  --input /path/to/nifty_data \
  --output orbiter/test_data/my_data.json \
  --limit 100
```

### Arguments

| Argument | Description | Default |
|----------|-------------|---------|
| `--input`, `-i` | Input directory with CSV files | (required) |
| `--output`, `-o` | Output JSON file | `orbiter/test_data/nifty_full.json` |
| `--limit`, `-l` | Max candles per symbol | All |

### Expected CSV Format

The converter expects CSV files in format:

```csv
date,open,high,low,close,volume
2015-02-02 09:15:00,216.45,217.15,216.3,216.4,229342
2015-02-02 09:16:00,216.4,216.55,216.0,216.0,97732
...
```

The converter automatically filters to market hours (9:15 - 15:30).

## How It Works

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Orbiter Main                           │
└─────────────────────┬───────────────────────────────────────┘
                      │
        ┌─────────────▼─────────────┐
        │    EngineFactory          │
        │  (build_engine)           │
        └─────────────┬─────────────┘
                      │
        ┌─────────────▼─────────────┐
        │  --mock_data=true?        │
        └─────────────┬─────────────┘
                      │
          ┌───────────┴───────────┐
          │                       │
          ▼                       ▼
   ┌──────────────┐      ┌──────────────────┐
   │ MockBroker   │      │  BrokerClient    │
   │ (mock_client)│      │  (real websocket)│
   └──────────────┘      └──────────────────┘
          │                       │
          ▼                       ▼
   ┌──────────────┐      ┌──────────────────┐
   │ JSON File    │      │  Shoonya API     │
   │ Replay       │      │  Live Feed       │
   └──────────────┘      └──────────────────┘
```

### Key Components

1. **MockBrokerClient** (`orbiter/core/broker/mock_client.py`)
   - Implements same interface as BrokerClient
   - Loads candle data from JSON files
   - Provides `SYMBOLDICT`, `prime_candles()`, `get_ltp()` etc.

2. **EngineFactory** (`orbiter/core/engine/builder/engine_factory.py`)
   - Checks for `--mock_data` flag in context
   - Routes to MockBrokerClient when enabled

3. **ArgumentParser** (`orbiter/utils/argument_parser.py`)
   - Parses `--mock_data` and `--mock_data_file` CLI args

4. **SessionManager** (`orbiter/core/engine/session/session_manager.py`)
   - Modified to not trigger EOD shutdown when `ORBITER_SIMULATE_MARKET_HOURS=true`

## Limitations

### Current Limitations

1. **Token Matching**: The mock broker matches symbols by name, not exact tokens. If your strategy expects NFO option tokens (e.g., 26013 for NIFTY options) but your data has equity tokens (e.g., 26000 for NIFTY index), some lookups may fail.

2. **Option Resolution**: The mock resolver (`MockResolver`) returns `mock_mode` for option strike resolution. To test actual option trading, you need:
   - Real F&O data captured during market hours
   - Or mock the option chain resolution

3. **Order Execution**: Mock broker doesn't place real orders. It logs the attempt but returns mock responses.

### What Works

- ✅ Strategy rule evaluation
- ✅ Technical indicator calculation
- ✅ Scoring (ADX, EMA, Supertrend)
- ✅ Signal generation (trade.place_spread)
- ✅ Data priming from historical candles
- ✅ Market hours simulation

### What Doesn't Work (Needs Real Data)

- ❌ Option strike price resolution
- ❌ Real order placement
- ❌ Live websocket feed

## Troubleshooting

### "No symbols matched" Warning

```
WARNING | MockBrokerClient: No symbols matched! Data has: []
```

**Cause**: Data file not loaded properly.

**Fix**: 
- Check file path is correct
- Verify JSON is valid
- Ensure file exists and is readable

### "No data found for token=X" Warning

```
WARNING | No data found for token=26013, lookup_key=NSE|26013
```

**Cause**: Token mismatch between strategy and data.

**Fix**:
- The mock broker uses symbol name matching. Ensure your data has symbols that match the strategy's `instruments.json`.
- Use the converter with proper symbol names.

### EOD Shutdown Triggered

```
Rule matched: EOD Shutdown
Engine shutdown sequence triggered
```

**Cause**: Running without `ORBITER_SIMULATE_MARKET_HOURS=true`.

**Fix**:
```bash
export ORBITER_SIMULATE_MARKET_HOURS=true
python -m orbiter.main --mock_data=true ...
```

### "Resolution Failed: mock_mode"

```
ERROR | Resolution Failed: mock_mode
```

**Cause**: Mock resolver doesn't implement option strike resolution.

**Fix**: This is expected behavior. For full option trading tests, you need real F&O data.

## Data Collection During Market Hours

To capture your own data for testing:

### Using the WebSocket Collector

1. Run during market hours (9:15 AM - 3:30 PM IST):
```bash
cd /path/to/OrbiterTestData
python collect_websocket_data.py
```

2. The script will save data to JSON files in the same directory.

3. Use the captured data:
```bash
python -m orbiter.main \
  --mock_data=true \
  --mock_data_file=/path/to/captured_data.json \
  --strategyCode=n1
```

### Manual Collection

You can also capture data directly using the broker API:

```python
from orbiter.core.broker import BrokerClient

broker = BrokerClient(project_root, creds_path, segment_name='nfo')

# Get historical candles
candles = broker.api.get_time_price_series(
    exchange='NSE',
    token='26000',
    starttime=1704066600,  # epoch
    endtime=1704102600,
    interval='5'  # 5-minute candles
)

# Save to JSON
import json
with open('nifty_data.json', 'w') as f:
    json.dump({'NSE_NIFTY': {'symbol': 'NIFTY', 'token': '26000', 'exchange': 'NSE', 'candles': candles}}, f)
```

## Testing Example

Here's a complete test run:

```bash
# Set environment
export ORBITER_SIMULATE_MARKET_HOURS=true
export ORBITER_LOG_LEVEL=INFO

# Run with mock data
python -m orbiter.main \
  --paper_trade=true \
  --mock_data=true \
  --mock_data_file=orbiter/test_data/nifty_full.json \
  --strategyCode=n1
```

### Expected Output

```
✨ ORBITER v3.3.0-20260316-xxx | PID: xxx
✅ Lock acquired: /home/trading_ceo/python-trader/orbiter.lock
Building application context...
🚀 Loaded: Nifty FnO TopN Trend with 2 filter groups.
🚀 Generic Machine Started
[EngineFactory.build_engine] - Using MOCK broker (mock_data=true)
[EngineFactory.build_engine] - Using mock data file: orbiter/test_data/nifty_full.json
MockBrokerClient: Using custom data file from env: orbiter/test_data/nifty_full.json
MockBrokerClient: Loaded 266 instruments from orbiter/test_data/nifty_full.json
MockBrokerClient: Primed 41/53 symbols
✅ Broker reporting zero open positions.
📊 Universe: 53 tokens loaded for NFO
🎯 Entry Threshold: Nonepts
[EngineFactory.build_engine] - Engine build process complete. Returning Engine instance.
✅ Engine initialized successfully.
...
✅ Rule matched: Market Open Loop
⚡ SYSTEM ACTION: engine.tick | Params: {}
🔄 ENGINE TICK (full scan) - Universe: 53 symbols
📊 NIFTY: Score 17.26 (sum_bi=17.256036176479032, sum_uni=0.0)
✅ Rule matched: Nifty_FNO_TopN_Trend_Nifty_Execution
⚡ SYSTEM ACTION: trade.place_spread | Params: {'side': 'BUY', ...}
```

## Future Enhancements

Planned improvements:

1. **Tick-level replay**: Replay tick-by-tick instead of candles
2. **Option chain mock**: Generate synthetic option data from underlying
3. **Order mock**: Mock order execution and P&L calculation
4. **Scenario playback**: Pre-defined market scenarios for testing

## References

- Main branch: `orbiter/core/broker/mock_client.py`
- Engine integration: `orbiter/core/engine/builder/engine_factory.py`
- CLI parsing: `orbiter/utils/argument_parser.py`
- Test data: `orbiter/test_data/`
- Data converter: `orbiter/test_data/convert_nifty_data.py`
