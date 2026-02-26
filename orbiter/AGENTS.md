# ORBITER - Trading System Documentation

## CLI Flags

### Trading Modes

| Flag | Description | Example |
|------|-------------|---------|
| `--paper_trade=true` | Paper trading - no real orders placed | `--paper_trade=true` |
| `--paper_trade=false` | Real trading - place actual orders with broker | `--paper_trade=false` |

**Default:** `paper_trade=true` (safe default - always paper trade unless explicitly set to false)

### Market Hours

| Flag | Environment Variable | Description |
|------|---------------------|-------------|
| | `ORBITER_SIMULATE_MARKET_HOURS=true` | Run outside market hours (e.g., 7 PM) |

**When to use:**
- `ORBITER_SIMULATE_MARKET_HOURS=true` - Testing at home after market closes
- Without this flag - Only runs during market hours (9:15 AM - 3:30 PM IST)

### Strategy Selection

| Flag | Description | Example |
|------|-------------|---------|
| `--strategyCode=s1` | Use specific strategy code | `--strategyCode=s1` |
| `--strategyCode=n1` | Use NIFTY strategy | `--strategyCode=n1` |
| `--strategyExecution=dynamic` | Auto-select strategy based on market regime | `--strategyExecution=dynamic` |

**Strategy Codes:**
- `m1` - MCX Trend Follower
- `n1` - Nifty FnO TopN Trend  
- `n2` - Nifty 50 Expiry Day Short Straddle
- `s1` - BSE SENSEX F&O TopN Trend
- `s2` - BSE SENSEX Expiry Day Short Straddle

### Office Mode

| Flag | Description |
|------|-------------|
| `--office_mode=true` | MBP taking over from RPI - sends freeze command to RPI via Telegram |

## Environment Variables

| Variable | Values | Description |
|----------|--------|-------------|
| `ORBITER_SIMULATE_MARKET_HOURS` | `true`/`false` | Run even when markets are closed |
| `ORBITER_LOG_LEVEL` | `INFO`/`DEBUG`/`TRACE` | Logging verbosity |
| `ORBITER_2FA` | TOTP code | Override 2FA token |

## Usage Examples

### Test at home (outside market hours)
```bash
ORBITER_SIMULATE_MARKET_HOURS=true python main.py --paper_trade=true --strategyCode=s1
```

### Paper trade during market hours
```bash
python main.py --paper_trade=true --strategyCode=s1
```

### Live trading during market hours
```bash
python main.py --paper_trade=false --strategyCode=s1
```

### Dynamic strategy selection (auto-select based on ADX)
```bash
ORBITER_SIMULATE_MARKET_HOURS=true python main.py --paper_trade=true --strategyExecution=dynamic
```

### Office mode (MBP takes over from RPI)
```bash
python main.py --office_mode=true --paper_trade=false
```

## Mode Matrix

| Scenario | Paper Trade | Simulate Market Hours | Result |
|----------|-------------|----------------------|--------|
| Testing at home after hours | true | true | ✅ Run, no trades |
| Paper trade during hours | true | false | ✅ Run, no trades |
| Live trade during hours | false | false | ✅ Run, real trades |
| Test live at home | false | true | ⚠️ Run, real trades |
| Office mode takeover | false | false | ✅ Run, live + freeze RPI |

## Dynamic Strategy Selection

When using `--strategyExecution=dynamic`, the system:
1. Fetches SENSEX ADX from Yahoo Finance
2. If ADX >= 25 → selects trending strategy (s1)
3. If ADX < 25 → selects sideways strategy (s2)

This runs at startup to determine market regime for the day.
