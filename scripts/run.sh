#!/usr/bin/env bash
set -euo pipefail

# Default run script: Forwards to NFO run script
SCRIPTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# If user passed arguments, pass them along
# By default, this will run NFO
exec "$SCRIPTS_DIR/run_nfo.sh" "$@"
