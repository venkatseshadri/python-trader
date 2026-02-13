#!/usr/bin/env bash
set -euo pipefail

SCRIPTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Call NFO run script with forced simulation
echo "🧪 Starting Orbiter NFO SIMULATION..."
exec "$SCRIPTS_DIR/run_nfo.sh" --simulation "$@"
