# Mock Data Testing for Orbiter

This document describes the mock data feature for testing Orbiter outside market hours using pre-recorded data.

## Overview

Mock data replaces the real broker connection with file-based replay, enabling:
- Off-hours testing
- Historical replay
- CI/CD testing without live APIs

## Quick Start

```bash
# Simulation mode (default - no broker calls)
python3 orbiter/main.py --mode=simulation --caller=bot

# With custom mock data file
python3 orbiter/main.py --mode=simulation --mock_data_file=orbiter/test_data/nifty_full.json --strategyCode=n1
```

## CLI Arguments

| Argument | Values | Description |
|----------|--------|-------------|
| `--caller` | `bot`, `user`, `cron` | Who triggered Orbiter |
| `--logLevel` | `TRACE`, `DEBUG`, `INFO` | Logging verbosity |
| `--mode` | `simulation`, `paper`, `live` | Trading mode |
| `--strategyCode` | `n1`, `n2`, `s1`, `s2`, `m1` | Strategy code |
| `--mock_data_file` | `/path/to/data.json` | Test data file |

### Environment Variables

| Variable | Description |
|----------|-------------|
| `ORBITER_SIMULATE_MARKET_HOURS` | Force market open state (`true`/`false`) |
| `ORBITER_MOCK_DATA_FILE` | Override data file path |
| `ORBITER_LOG_LEVEL` | Logging level |

## Data File Format

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
      }
    ]
  }
}
```

| Field | Description |
|-------|-------------|
| `symbol` | Trading symbol |
| `token` | Exchange token |
| `exchange` | NSE, BFO, MCX |
| `candles` | OHLCV array |
| `into/inth/intl/intc` | Open/High/Low/Close |
| `intv` | Volume |
| `oi` | Open Interest |

## Test Data Files

| File | Description |
|------|-------------|
| `orbiter/test_data/nfo_data.json` | NSE F&O sample |
| `orbiter/test_data/bfo_data.json` | BSE F&O sample |
| `orbiter/test_data/mcx_data.json` | MCX commodities |
| `orbiter/test_data/nifty_full.json` | Nifty 50 stocks |

## Architecture

```
main.py
    │
    ▼
ArgumentParser.parse_cli_to_facts()
    │  └── Detects --mode=simulation
    ▼
EngineFactory.build_engine()
    │
    ├─► mode=simulation? ──► MockBrokerClient
    │                              │
    │                              ▼
    │                         JSON File Replay
    │
    └─► mode=live? ──► BrokerClient
                           │
                           ▼
                      Live WebSocket
```

## How It Works

1. **ArgumentParser** detects `--mode=simulation` or `--mock_data_file`
2. **EngineFactory** routes to MockBrokerClient when simulation mode
3. **MockBrokerClient** loads JSON and replays candles
4. **SessionManager** skips EOD shutdown when `ORBITER_SIMULATE_MARKET_HOURS=true`

## Limitations

| Works | Doesn't Work |
|-------|-------------|
| ✅ Strategy evaluation | ❌ Real order placement |
| ✅ Technical indicators | ❌ Live websocket |
| ✅ Scoring | ❌ Option strike resolution |
| ✅ Signal generation | |

## Troubleshooting

### "No symbols matched"

**Cause:** Data file not loaded.

**Fix:** Check file path is correct and JSON is valid.

### "No data found for token=X"

**Cause:** Token mismatch between strategy and data.

**Fix:** Ensure data symbols match `instruments.json`.

### EOD Shutdown triggered

**Fix:**
```bash
export ORBITER_SIMULATE_MARKET_HOURS=true
python3 orbiter/main.py --mode=simulation ...
```

## Testing Example

```bash
export ORBITER_SIMULATE_MARKET_HOURS=true
export ORBITER_LOG_LEVEL=INFO

python3 orbiter/main.py \
  --mode=simulation \
  --mock_data_file=orbiter/test_data/nifty_full.json \
  --strategyCode=n1
```

### Expected Output

```
✨ ORBITER v4.6.1-xxx | PID: xxx
📋 CLI: caller=bot logLevel=INFO
📊 Mode: SIMULATION (default - captured data, no broker hits)
...
```

## References

- MockBrokerClient: `orbiter/core/broker/mock_client.py`
- EngineFactory: `orbiter/core/engine/builder/engine_factory.py`
- ArgumentParser: `orbiter/utils/argument_parser.py`
