# ORBITER - Trading System Documentation

> **Quick Links:**
> - [Architecture Docs](./docs/ARCHITECTURE.md)
> - [Configuration Docs](./docs/CONFIGURATION.md)

## Quick Reference

| What you want... | Command |
|-----------------|---------|
| Test at home (after market) | `ORBITER_SIMULATE_MARKET_HOURS=true python -m orbiter.main --strategyCode=m1` |
| Paper trade live | `python -m orbiter.main --strategyCode=m1` |
| Live trade | `python -m orbiter.main --real_broker_trade=true --strategyCode=m1` |

## CLI Flags (Command Line Arguments)

### Trading Modes

| Flag | Description |
|------|-------------|
| `--real_broker_trade=true` | Real trading - place actual orders |
| `--real_broker_trade=false` | Paper trading - no real orders placed (DEFAULT) |

**Default:** `real_broker_trade=false` (always paper trading for safety)

### Strategy Selection

| Flag | Description | Example |
|------|-------------|---------|
| `--strategyCode=m1` | MCX Trend Follower | Commodities |
| `--strategyCode=n1` | Nifty FnO TopN Trend | Nifty F&O |
| `--strategyCode=n2` | Nifty Expiry Day Short Straddle | Nifty Options |
| `--strategyCode=s1` | BSE SENSEX F&O TopN Trend | Sensex F&O |
| `--strategyCode=s2` | BSE SENSEX Expiry Day Short Straddle | Sensex Options |
| `--strategyExecution=dynamic` | Auto-select strategy based on ADX | |

### Paper Positions

| Flag | Description |
|------|-------------|
| `--clear_paper_positions=true` | Clear all existing paper positions on startup (start fresh) |

On startup, Orbiter loads existing paper positions from disk. If positions exist, a warning is logged:
```
⚠️  N existing paper positions loaded. Use --clear_paper_positions=true to start fresh.
```

This is important for strategies like Iron Condor that only trade when `portfolio.active_positions == 0`.

### Alternative Syntax

| Flag | Also works as |
|------|---------------|
| `--strategyCode=s1` | `--strategy_code=s1`, `--strategyId=bsensex_bfo_topn_trend` |
| `--real_broker_trade=true` | Live trading - place actual orders |

## Environment Variables

| Variable | Values | Description |
|----------|--------|-------------|
| `ORBITER_SIMULATE_MARKET_HOURS` | `true` or `false` | Run outside market hours (9:15 AM - 3:30 PM IST) |
| `ORBITER_LOG_LEVEL` | `TRACE`, `DEBUG`, `INFO`, `WARNING`, `ERROR` | Logging verbosity |
| `ORBITER_2FA` | TOTP code | Override 2FA (normally auto-generated) |

## Data Priming (Historical Data)

On startup, Orbiter loads historical candles to calculate technical indicators:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `priming_lookback_mins` | 120 | How many minutes of history to load |
| `priming_interval` | 5 | Candle interval in minutes |

This gives ~24 bars of 5-minute data, which is enough for most indicators (ADX needs 14+ periods).

**Note:** Historical data only works when market is OPEN. Outside market hours, you'll see "Bars: 0" or "Bars: 1" because the API doesn't return historical data. The system will still work once market opens and WebSocket data starts streaming.

### ADX Fallback

When broker historical data is insufficient (less than 12 candles), Orbiter automatically falls back to Yahoo Finance for ADX calculation:

| Exchange | Yahoo Finance Index | Symbol |
|----------|-------------------|--------|
| NFO | NIFTY | ^NSEI |
| BFO | SENSEX | ^BSESN |
| MCX | **No fallback** | Returns zeros |

- Caches the value for 5 minutes to avoid excessive API calls
- This ensures scoring works even outside market hours
- MCX returns zeros (no fallback) to avoid false signals from equity indices

The YF ADX is used for scoring only. For dynamic strategy selection, the system already uses Yahoo Finance directly at startup.

## Usage Examples

### Test at home (outside market hours)
```bash
ORBITER_SIMULATE_MARKET_HOURS=true python -m orbiter.main --strategyCode=s1
```

### Paper trade during market hours
```bash
python -m orbiter.main --strategyCode=s1
```

### Live trading during market hours
```bash
python -m orbiter.main --real_broker_trade=true --strategyCode=s1
```

### Debug mode (verbose logging)
```bash
ORBITER_LOG_LEVEL=TRACE python -m orbiter.main --strategyCode=m1
```

### Dynamic strategy selection (auto-select based on ADX)
```bash
ORBITER_SIMULATE_MARKET_HOURS=true python -m orbiter.main --strategyExecution=dynamic
```

## Mode Matrix

| Scenario | Real Broker Trade | Simulate Market Hours | Result |
|----------|-------------------|----------------------|--------|
| Testing at home after hours | false | true | Run, no trades |
| Paper trade during hours | false | false | Run, no trades |
| Live trade during hours | true | false | Run, real trades |
| Test live at home | true | true | Run, real trades |

## Dynamic Strategy Selection

When using `--strategyExecution=dynamic`, the system:
1. Fetches SENSEX ADX from Yahoo Finance
2. If ADX >= 25 → selects trending strategy (s1)
3. If ADX < 25 → selects sideways strategy (s2)

This runs at startup to determine market regime for the day.

## MCX Futures Update

MCX contracts expire monthly. The system uses `config/mcx/mcx_instruments.json` for instrument configuration.

### Manual Update (Tokens & Margins)

To get latest tokens and margin requirements:

```bash
python orbiter/tools/mcx_risk_audit_v4_0.py
```

This will update:
- `config/mcx/mcx_instruments.json` - tokens, lot sizes, margins
- `data/mcx_futures_map.json` - futures mapping

### MCX Instruments Config

The system now uses `config/mcx/mcx_instruments.json` for MCX trading:

```json
{
  "instruments": [
    {
      "symbol": "CRUDEOILM",
      "token": "472790",
      "lot_size": 10,
      "margin_per_lot": 38149
    }
  ]
}
```

### Margin Check Before Trade

The executor now checks available margin before placing MCX trades:
- Fetches available margin from broker
- Blocks trade if insufficient margin
- Logs: `⛔ MARGIN BLOCK: Need ₹X but only ₹Y available`

Helper functions in `config/mcx/config.py`:
- `get_mcx_margin(symbol)` - returns required margin
- `get_mcx_lot_size(symbol)` - returns lot size

> **Note:** Token keys are symbol names (e.g., "CRUDEOIL"), not numeric tokens. Token resolution happens via ScripMaster.

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
4. If ADX is showing 0, check if broker candles are available (outside market hours, YF fallback is used)

### ADX Shows 0 in Scoring

If ADX shows 0 despite having data:
1. Check broker candles: `ORBITER_LOG_LEVEL=TRACE` - look for "Bars: X" in logs
2. If Bars < 20, system uses YF fallback - verify internet connectivity
3. YF fallback is cached for 5 minutes - restart or wait for cache expiry

### Lock File Error

```bash
rm -f /home/trading_ceo/python-trader/orbiter.lock
```

### Session Expired

Orbiter now has auto-reconnect - it will automatically re-authenticate when session expires. If it keeps failing:
1. Check credentials in `ShoonyaApi-py/cred.yml`
2. Ensure TOTP key is valid
3. Check broker API status
