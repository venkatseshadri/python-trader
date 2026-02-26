# Last Technical Change: MCX Trading & VPS Deployment

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
