#!/bin/bash
# pyuser.sh - Wrapper to run Orbiter with --caller=user automatically
# Usage: ./pyuser.sh [strategyCode] [other args...]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR"

cd "$PROJECT_DIR" || exit 1

# Auto-inject --caller=user if not already passed
args=("$@")
caller_set=false
for arg in "${args[@]}"; do
    if [[ "$arg" == --caller=* ]]; then
        caller_set=true
        break
    fi
done

if [ "$caller_set" = false ]; then
    args+=("--caller=user")
fi

python3 orbiter/main.py "${args[@]}"