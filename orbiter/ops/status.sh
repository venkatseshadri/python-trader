#!/bin/bash
# Quick status check for Orbiter
# Usage: ./status.sh

echo "📊 Orbiter Quick Status"
echo "======================="
echo ""

# Check binary
if [ -f "/home/trading_ceo/python-trader/dist/orbiter-4.6.1" ]; then
    echo "✅ Binary: Found"
else
    echo "❌ Binary: Missing"
fi

echo ""

# Check strategies
for strat in n1 n2 s1 s2 m1; do
    log_file="/tmp/orbiter_${strat}.log"
    if [ -f "$log_file" ]; then
        size=$(stat -c%s "$log_file" 2>/dev/null || echo 0)
        if [ $size -gt 0 ]; then
            # Get last few lines for errors
            errors=$(grep -c "ERROR\|Error\|error" "$log_file" 2>/dev/null || echo 0)
            last_mod=$(stat -c "%y" "$log_file" | cut -d' ' -f2 | cut -d':' -f1,2)
            echo "🟢 $strat: Log exists ($size bytes) - Last: $last_mod - Errors: $errors"
        else
            echo "🟡 $strat: Log empty"
        fi
    else
        echo "🔴 $strat: No log file"
    fi
done

echo ""

# Check paper positions
if [ -s "/home/trading_ceo/python-trader/orbiter/data/paper_positions.json" ]; then
    echo "✅ Paper Positions: OK"
else
    echo "❌ Paper Positions: Empty or corrupted"
fi

echo ""

# Check cron
echo "⏰ Cron Status:"
crontab -l | grep orbiter || echo "   No orbiter cron job"

echo ""
echo "======================="
