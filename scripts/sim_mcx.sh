#!/usr/bin/env bash
set -euo pipefail

SCRIPTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Call MCX run script with forced simulation
echo "🧪 Starting Orbiter MCX SIMULATION..."
exec "$SCRIPTS_DIR/run_mcx.sh" --simulation "$@"
