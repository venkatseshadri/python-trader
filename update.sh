#!/bin/bash

# 🚀 ORBITER Raspberry Pi Update & Maintenance Script
# This script automates pulling changes, installing dependencies, and restarting the daemon.

echo "⏳ Starting Update..."

# 0. Check current state before pull
PRE_PULL_HASH=$(git rev-parse HEAD)

# 1. Pull latest changes from GitHub
echo "📥 Pulling latest code..."
git pull origin main

POST_PULL_HASH=$(git rev-parse HEAD)

# 2. Check for Core Changes (Determines if restart is needed)
# We look for changes in orbiter/, API, config, or the update scripts themselves
CORE_CHANGES=$(git diff --name-only $PRE_PULL_HASH $POST_PULL_HASH | grep -E "^(orbiter/|ShoonyaApi-py/|config/|requirements.txt|update.sh|release.sh)")

if [ -n "$CORE_CHANGES" ] || [ "$PRE_PULL_HASH" == "$POST_PULL_HASH" ]; then
    # If core files changed OR if forced run (no changes pulled), we allow restart logic
    RESTART_REQUIRED=true
    echo "⚡ Core changes detected or forced update. Restart will be performed if service exists."
else
    RESTART_REQUIRED=false
    echo "📄 Non-core changes (docs/lab/etc). Skipping restart to maintain session stability."
fi

# 3. Update dependencies (only if requirements changed)
if [ -d ".venv" ]; then
    echo "📦 Updating dependencies in .venv..."
    ./.venv/bin/pip install -q -r orbiter/requirements.txt
elif [ -d "shoonya_env" ]; then
    echo "📦 Updating dependencies in shoonya_env..."
    ./shoonya_env/bin/pip install -q -r orbiter/requirements.txt
else
    echo "📦 Updating system dependencies..."
    pip install -q -r orbiter/requirements.txt
fi

# 4. Verify File Integrity
echo "🛡️ Verifying file integrity..."
if [ -f "checksums.txt" ]; then
    FAILED_LIST=$(shasum -a 256 -c checksums.txt 2>/dev/null | grep "FAILED" | cut -d':' -f1)
    FAILED_COUNT=$(echo "$FAILED_LIST" | grep -v '^$' | wc -l)
    
    if [ "$FAILED_COUNT" -eq "0" ]; then
        echo "✅ Integrity check passed!"
    else
        echo "⚠️ WARNING: $FAILED_COUNT files failed the integrity check."
        echo "Top 5 failures:"
        echo "$FAILED_LIST" | head -n 5
        echo "Check checksums.txt and local diffs for details."
    fi
else
    echo "ℹ️ No checksums.txt found, skipping integrity check."
fi

# 5. Manage Systemd Service
if [ "$RESTART_REQUIRED" = true ]; then
    if [ -f "/etc/systemd/system/orbiter.service" ]; then
        echo "🔄 Reloading and Restarting Orbiter service..."
        sudo systemctl daemon-reload
        sudo systemctl restart orbiter
        echo "✅ Service restarted!"
    else
        echo "ℹ️ Systemd service not found. Skipping restart."
    fi
else
    echo "⏭️ Skipping service restart (Non-critical changes only)."
fi

# 6. Check Status
if command -v systemctl &> /dev/null && systemctl is-active --quiet orbiter; then
    echo "🟢 Orbiter is now running."
else
    if [ "$RESTART_REQUIRED" = true ]; then
        echo "🔴 Orbiter is NOT running. Check logs with: journalctl -u orbiter -f"
    fi
fi

echo "✨ Update Complete! Build version: $(cat version.txt 2>/dev/null)"
