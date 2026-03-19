# Last Technical Change: CLI Refactor - real_broker_trade Flag

**Date:** 2026-03-19
**Status:** COMPLETED (Build: `v4.3.0`)

## v4.3.0 Changes

### CLI Refactor: --real_broker_trade Flag
- Replaced `--paper_trade` with `--real_broker_trade`
- Default is `real_broker_trade=false` (paper trading for safety)
- Use `--real_broker_trade=true` to enable live trading
- Updated AGENTS.md documentation

### Previous: Session Auto-Reconnect & Bug Fixes

**Date:** 2026-03-19
**Status:** COMPLETED (Build: `v4.2.0`)

## v4.2.0 Changes

### 1. Auto-Reconnect on Session Expiry
- Added `_is_session_expired()` to detect broker session expiry
- Added `_handle_api_call()` wrapper for automatic re-authentication
- Applied to: get_limits, get_positions, get_order_history, get_option_ltp_by_symbol, get_option_theta
- Max 2 retry attempts before giving up

### 2. Fixed "No Data" Error
- Fixed broker API calls using trading symbol instead of numeric token
- Now looks up numeric token from SYMBOL_TO_TOKEN master before API call
- Resolved "Error Occurred : 5 no data" responses

### 3. Code Cleanup
- Removed `office_mode` completely from codebase
- Removed `config_path` parameter from BrokerClient (ConnectionManager handles auth)
- Fixed BrokerClient call in engine_factory.py

### 4. Version Format
- Now using A.B.C format: 4.2.0, 4.2.1, 4.3.0, 5.0.0
- Minor fixes: patch version (x.x.1)
- New features: minor version (x.3.0)
- Major changes: major version (5.0.0)

---

# Previous: MCX Trading & VPS Deployment

**Date:** 2026-02-26
**Status:** COMPLETED (Build: `v3.3.0-20260226`)

## Today's Changes

### 1. MCX Trading Support
- Added `exchange_config.json` with product codes for MCX/NFO/BFO
- Product codes: `I` = Intraday/MIS, `M` = NRML/Carry Forward
- Fixed futures executor to read product/price_type from config
- Fixed resolver to sort by expiry date (not string) to pick nearest contract

### 2. MCX Contract Resolution
- Added `update_mcx_config.py` utility to fetch latest MCX contracts from broker API
- Uses `searchscrip` to get real-time contracts
- Filters out expired contracts automatically

### 3. Paper Trading Fix
- Fixed `paper_trade` flag not flowing to executors
- Added paper_trade check to equity.py and options.py executors
- Now properly simulates orders when `--paper_trade=true`

### 4. Action Types Cleanup
- Changed all strategies to use `trade.place_spread` (not `trade.place_order`)
- Updated constants.json and registration_manager.py
- Updated rules.json for all strategies

### 5. VPS Deployment (Hostinger)
- Created user `trader` (not running as root)
- Installed dependencies: TA-Lib, gspread, rule_engine, etc.
- Created systemd service at `/etc/systemd/system/orbiter.service`
- Added `switch.sh` script for easy strategy switching

### 6. Switch Script
Location: `orbiter/switch.sh`

```bash
# Paper trade (default)
./orbiter/switch.sh n1

# Live trading
./orbiter/switch.sh n1 --paper=false

# Live, real market hours (no simulation)
./orbiter/switch.sh n2 --paper=false --sim=false

# MCX
./orbiter/switch.sh m1 --paper=false
```

## Strategy Codes
| Code | Strategy |
|------|----------|
| n1 | Nifty F&O TopN Trend |
| n2 | Nifty Expiry Day Short Straddle |
| m1 | MCX Trend Follower |
| s1 | BSE Sensex TopN Trend |
| s2 | BSE Sensex Expiry Day Short Straddle |

## VPS Access
- IP: 187.77.188.100
- User: trader
- Service: `systemctl status orbiter`
- Logs: `journalctl -u orbiter -f`

## Known Issues
- TRACE logging still enabled (produces verbose output)
- Some LSP type errors in executors (non-blocking)
