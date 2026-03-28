# Orbiter CLI & Configuration

Quick reference for command-line arguments and configuration files.

---

## CLI Arguments

| Argument | Values | Description |
|----------|--------|-------------|
| `--caller` | `bot`, `user`, `cron` | Who triggered Orbiter |
| `--logLevel` | `TRACE`, `DEBUG`, `INFO`, `WARNING`, `ERROR` | Logging verbosity |
| `--mode` | `simulation`, `paper`, `live` | Trading mode |
| `--strategyCode` | `n1`, `n2`, `s1`, `s2`, `m1`, `x1` | Strategy to run |
| `--mock_data_file` | `/path/to/data.json` | Test data file (optional) |

### Usage Examples

```bash
# Default run (simulation mode, no broker calls)
python3 orbiter/main.py --caller=bot --logLevel=INFO

# Paper trading (live data, no orders)
python3 orbiter/main.py --caller=bot --mode=paper --strategyCode=n1

# Live trading
python3 orbiter/main.py --caller=user --mode=live --strategyCode=m1

# With custom mock data (testing)
python3 orbiter/main.py --mode=simulation --mock_data_file=orbiter/test_data/nifty_full.json
```

### Mode Details

| Mode | Broker | Orders | Use Case |
|------|-------|--------|---------|
| `simulation` | Mock | No | Testing, off-hours |
| `paper` | Live | No | Paper trading |
| `live` | Live | Yes | Real trading |

---

## Configuration Files

Located in `orbiter/config/`:

| File | Purpose |
|------|---------|
| `manifest.json` | Master registry of all config files |
| `constants.json` | Hardcoded strings (messages, keys) |
| `config.json` | Strategy codes, defaults |
| `global_config.json` | Global trading params (optional) |
| `session.json` | Broker credentials path |

### config.json

```json
{
  "default_strategy": "mcx_trend_follower",
  "strategy_codes": {
    "m1": "mcx_trend_follower",
    "n1": "nifty_fno_topn_trend",
    "n2": "nifty_50_nfo_expiry_day_short_straddle",
    "s1": "bsensex_bfo_topn_trend",
    "s2": "sensex_bfo_expiry_day_short_straddle"
  }
}
```

### global_config.json (optional)

```json
{
  "trade_score_threshold": 0.40,
  "top_n": 1,
  "max_daily_loss": 5000,
  "update_interval": 5
}
```

---

## Strategy Structure

```
orbiter/strategies/
├── mcx_trend_follower/
│   ├── strategy.json
│   ├── rules.json
│   ├── filters.json
│   └── instruments.json
├── nifty_fno_topn_trend/
│   └── ...
```

---

## Environment Variables

| Variable | Values | Description |
|----------|--------|-------------|
| `ORBITER_LOG_LEVEL` | TRACE/DEBUG/INFO/WARNING/ERROR | Override log level |
| `ORBITER_2FA` | TOTP code | Override 2FA token |
| `ORBITER_SIMULATE_MARKET_HOURS` | true/false | Force market open |

---

## Logging

Set via CLI or environment:

```bash
# CLI (recommended)
python3 orbiter/main.py --caller=bot --logLevel=TRACE

# Environment
export ORBITER_LOG_LEVEL=DEBUG
```

### Levels

| Level | Usage |
|-------|-------|
| `TRACE` | Function entry, full variable dumps |
| `DEBUG` | API calls, state changes |
| `INFO` | Ticks, scores, orders |
| `WARNING` | Recoverable issues |
| `ERROR` | Needs attention |
| `CRITICAL` | Fatal |

---

## CLI Context (Internal)

The parser produces these fields (exposed in debug logs):

```python
{
    'mode': 'simulation',           # simulation/paper/live
    'strategyid': 'mcx_trend_follower',  # resolved strategy name
    'caller': 'bot',                # bot/user/cron
    'loglevel': 'INFO',             # current log level
    'mock_data_file': None          # only if provided
}
```
