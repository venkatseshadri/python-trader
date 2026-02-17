#!/bin/bash

# 🚀 ORBITER Raspberry Pi Update & Maintenance Script
# This script automates pulling changes, installing dependencies, and restarting the daemon.

echo "⏳ Starting Update..."

# 1. Pull latest changes from GitHub
echo "📥 Pulling latest code..."
git pull origin main

# 2. Update dependencies (using the virtual environment if present)
if [ -d ".venv" ]; then
    echo "📦 Updating dependencies in .venv..."
    ./.venv/bin/pip install -r orbiter/requirements.txt
elif [ -d "shoonya_env" ]; then
    echo "📦 Updating dependencies in shoonya_env..."
    ./shoonya_env/bin/pip install -r orbiter/requirements.txt
else
    echo "📦 Updating system dependencies..."
    pip install -r orbiter/requirements.txt
fi

# 3. Verify File Integrity
echo "🛡️ Verifying file integrity..."
if [ -f "checksums.txt" ]; then
    FAILED=$(shasum -a 256 -c checksums.txt 2>/dev/null | grep -c "FAILED")
    if [ "$FAILED" -eq "0" ]; then
        echo "✅ Integrity check passed!"
    else
        echo "⚠️ WARNING: $FAILED files failed the integrity check. Check checksums.txt for details."
    fi
else
    echo "ℹ️ No checksums.txt found, skipping integrity check."
fi

# 4. Manage Systemd Service
if [ -f "/etc/systemd/system/orbiter.service" ]; then
    echo "🔄 Reloading and Restarting Orbiter service..."
    sudo systemctl daemon-reload
    sudo systemctl restart orbiter
    echo "✅ Service restarted!"
else
    echo "ℹ️ Systemd service not found in /etc/systemd/system/. Run setup instructions from README to enable it."
fi

# 5. Check Status
if command -v systemctl &> /dev/null && systemctl is-active --quiet orbiter; then
    echo "🟢 Orbiter is now running."
else
    echo "🔴 Orbiter is NOT running. Check logs with: journalctl -u orbiter -f"
fi

echo "✨ Update Complete! Build version: $(cat version.txt 2>/dev/null)"
