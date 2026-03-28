#!/bin/bash
# pybot.sh - Wrapper to run Orbiter with --caller=bot automatically
# Usage: ./pybot.sh [strategyCode] [other args...]
# Example: ./pybot.sh --strategyCode=N1 --logLevel=TRACE

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR"

cd "$PROJECT_DIR" || exit 1

# Auto-inject --caller=bot if not already passed
args=("$@")
caller_set=false
for arg in "${args[@]}"; do
    if [[ "$arg" == --caller=* ]]; then
        caller_set=true
        break
    fi
done

if [ "$caller_set" = false ]; then
    args+=("--caller=bot")
fi

# Run orbiter
python3 orbiter/main.py "${args[@]}"