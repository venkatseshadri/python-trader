#!/bin/bash
# Varaha Trading Bot - Market-aware Wrapper with Process Lock
# Checks: market open, prevents duplicate instances, kills stale processes

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MARKET_CHECK="/root/.picoclaw/workspace/scripts/check_market_open.sh"
PROCESS_LOCK="/root/.picoclaw/workspace/scripts/process_lock.sh"

echo "[VARAHA] Starting with market/lock checks..."

# Check if helper scripts exist
if [ ! -f "$MARKET_CHECK" ]; then
    echo "[ERROR] Market check script not found: $MARKET_CHECK"
    exit 1
fi

if [ ! -f "$PROCESS_LOCK" ]; then
    echo "[ERROR] Process lock script not found: $PROCESS_LOCK"
    exit 1
fi

# Check market status
echo "[VARAHA] Checking market status..."
bash "$MARKET_CHECK"
MARKET_STATUS=$?

if [ $MARKET_STATUS -ne 0 ]; then
    echo "[VARAHA] Market is closed. Skipping trading session."
    exit 0  # Exit cleanly, not an error
fi

# Check for existing instances (max 360 min = 6 hours, grace 2 min)
echo "[VARAHA] Checking for existing instances..."
bash "$PROCESS_LOCK" "varaha" 360 2
LOCK_STATUS=$?

if [ $LOCK_STATUS -ne 0 ]; then
    echo "[VARAHA] Could not acquire lock. Exiting."
    exit 0  # Exit cleanly
fi

# Market is open and lock acquired, run Varaha
echo "[VARAHA] Market is open and lock acquired. Starting trading bot..."
python3 "$SCRIPT_DIR/varaha_main.py" "$@"
