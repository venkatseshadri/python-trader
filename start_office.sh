#!/bin/bash
# 🏢 ORBITER OFFICE STARTUP SCRIPT (v1.0)
# This script handles the transition from RPI to MBC.

echo "🔄 Initializing Office Handover..."

# 1. Run the Handover Tool (Syncs code, Freezes RPI, Shows State)
python3 orbiter/handover.py

if [ $? -ne 0 ]; then
    echo "❌ Handover failed. Check your internet connection or credentials."
    exit 1
fi

echo ""
echo "❓ Choose Startup Mode:"
echo "1) 🚀 FULL NATIVE (Execution + Monitoring)"
echo "2) 🏢 OFFICE MODE (Monitoring Only)"
echo "3) ❌ Exit"
read -p "Selection [1-3]: " choice

case $choice in
    1)
        echo "🚀 Starting Orbiter in FULL NATIVE mode..."
        python3 orbiter/main.py
        ;;
    2)
        echo "🏢 Starting Orbiter in OFFICE MONITORING mode..."
        python3 orbiter/main.py --office-mode
        ;;
    3)
        echo "👋 Exiting."
        exit 0
        ;;
    *)
        echo "⚠️ Invalid selection. Starting in OFFICE MODE by default..."
        python3 orbiter/main.py --office-mode
        ;;
esac
