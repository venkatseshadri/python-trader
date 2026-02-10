#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="$ROOT_DIR/.venv"

if [[ ! -x "$VENV_DIR/bin/python" ]]; then
  echo "Missing venv. Run scripts/install.sh first."
  exit 1
fi

SIM_FLAG=""
if [[ "${1:-}" == "--simulation" ]]; then
  SIM_FLAG="--simulation"
fi

"$VENV_DIR/bin/python" "$ROOT_DIR/orbiter/strategies/orbiter.py" $SIM_FLAG
