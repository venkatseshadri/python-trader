# ORBITER - Trading System Documentation

> **Quick Links:**
> - [Architecture Docs](./docs/ARCHITECTURE.md)
> - [Configuration Docs](./docs/CONFIGURATION.md)

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

## MCX Futures Update

MCX contracts expire monthly. The system automatically checks for expired contracts and updates them.

### Manual Update

To manually update MCX contracts:

```bash
cd /Users/vseshadri/python
source .venv/bin/activate
PYTHONPATH=/Users/vseshadri/python python -m orbiter.utils.mcx.update_mcx_config
```

This will:
1. Connect to Shoonya broker
2. Search for current month futures for each commodity
3. Update `data/mcx_futures_map.json` with new tokens and expiry dates

### Auto-Update

The `ScripMaster.check_and_update_mcx_expiry()` method checks for expired contracts at startup and automatically calls the update utility if needed.

### mcx_futures_map.json Format

```json
{
  "472790": [
    "CRUDEOIL",
    "CRUDEOILM19MAR26",
    10,
    "19Mar26"
  ]
}
```

Format: `[symbol, trading_symbol, lot_size, expiry_date]`

## Scoring Flow

Scoring uses the strategy-specific rules.json:

1. **Scoring Rules** are defined in `rules.json` under `scoring_rules`
2. **Scoring Expression** uses facts from TechnicalAnalyzer and filter weights
3. **Filter Weights** are in `filters.json` under `scoring.combined_score`

Example scoring expression:
```
market_adx * filters_scoring_combined_score_weight_adx + (market_ema_fast - market_ema_slow) / market_ema_slow * 100 * filters_scoring_combined_score_weight_ema_slope + market_supertrend_dir * filters_scoring_combined_score_weight_supertrend
```

### Available Scoring Facts

| Fact | Source | Description |
|------|--------|-------------|
| `market_adx` | TechnicalAnalyzer | ADX indicator (0-100) |
| `market_ema_fast` | TechnicalAnalyzer | Fast EMA (5 period) |
| `market_ema_slow` | TechnicalAnalyzer | Slow EMA (20 period) |
| `market_supertrend_dir` | TechnicalAnalyzer | Direction: 1 (bull) or -1 (bear) |
| `filters_scoring_combined_score_weight_*` | filters.json | Configurable weights |

## Troubleshooting

### Scores are 0.00

Check:
1. Rules file is loaded (use TRACE logging)
2. Filter weights match scoring expression variables
3. Technical indicators are calculated

### Lock File Error

```bash
rm -f /Users/vseshadri/python/orbiter.lock
```

### Session Expired

Re-authenticate or check credentials in `ShoonyaApi-py/cred.yml`
