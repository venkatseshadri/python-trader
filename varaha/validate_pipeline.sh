#!/bin/bash
# Health Check Cron — Validate pipeline is running (9:15-15:30 weekdays)
# Runs every 5 minutes during market hours
# If master is dead, restart it cleanly

set -euo pipefail

PROJECT_ROOT="/home/trading_ceo/python-trader"
MASTER_SCRIPT="$PROJECT_ROOT/varaha/run_data_capture_with_v4.sh"
MASTER_LOCK="/tmp/data_capture_master.lock"
LOG_DIR="/tmp"
HEALTH_LOG="$LOG_DIR/pipeline_health.log"

timestamp=$(date "+%Y-%m-%d %H:%M:%S")

log_msg() {
    echo "[$timestamp] $1" >> "$HEALTH_LOG"
}

check_market_hours() {
    HOUR=$(date +%H)
    MIN=$(date +%M)
    WEEKDAY=$(date +%u)

    # Market hours: 9:15 AM - 3:30 PM, Monday-Friday
    if [ "$WEEKDAY" -ge 6 ]; then
        return 1  # Weekend
    fi

    if [ "$HOUR" -lt 9 ] || ([ "$HOUR" -eq 9 ] && [ "$MIN" -lt 15 ]); then
        return 1  # Before market open
    fi

    if [ "$HOUR" -gt 15 ] || ([ "$HOUR" -eq 15 ] && [ "$MIN" -ge 31 ]); then
        return 1  # After market close
    fi

    return 0  # Market hours
}

check_master_running() {
    if [ ! -f "$MASTER_LOCK" ]; then
        return 1  # No lock file
    fi

    MASTER_PID=$(cat "$MASTER_LOCK")
    if kill -0 "$MASTER_PID" 2>/dev/null; then
        return 0  # Master is alive
    else
        return 1  # Master is dead
    fi
}

count_processes() {
    ps aux | grep -E "data_capture_v3.1_duckdb.py|data_capture_v4_queue_aggregator.py" | grep -v grep | wc -l
}

restart_pipeline() {
    log_msg "❌ Master script dead or not running. Restarting..."

    # Cleanup stale processes
    pkill -9 -f "data_capture_v3.1_duckdb" 2>/dev/null || true
    pkill -9 -f "data_capture_v4_queue" 2>/dev/null || true
    sleep 1

    # Remove stale lock
    rm -f "$MASTER_LOCK"

    # Start fresh master script
    cd "$PROJECT_ROOT"
    nohup "$MASTER_SCRIPT" >>"$LOG_DIR/validate_pipeline.log" 2>&1 &

    log_msg "✅ Pipeline restarted (new master PID: $!)"
}

# ============================================================
# MAIN
# ============================================================

if ! check_market_hours; then
    # Outside market hours, don't check
    exit 0
fi

if check_master_running; then
    # Master is alive, check child processes
    PROC_COUNT=$(count_processes)

    if [ "$PROC_COUNT" -eq 3 ]; then
        # Perfect state: 1 v3.1 NIFTY + 1 v3.1 SENSEX + 1 v4
        log_msg "✅ Pipeline healthy ($PROC_COUNT processes)"
    elif [ "$PROC_COUNT" -gt 3 ]; then
        # Duplicates detected - master's watchdog should handle, but log it
        log_msg "⚠️  WARNING: $PROC_COUNT processes (expected 3) - duplicates detected"
    elif [ "$PROC_COUNT" -lt 3 ]; then
        # Missing processes - watchdog will restart them
        log_msg "⚠️  WARNING: $PROC_COUNT processes (expected 3) - watchdog should restart"
    fi
else
    # Master is dead - restart
    restart_pipeline
fi

exit 0
