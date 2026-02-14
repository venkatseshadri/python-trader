#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Find Python executable (Check project .venv, then parent shoonya_env)
if [[ -x "$ROOT_DIR/.venv/bin/python" ]]; then
  PYTHON_EXEC="$ROOT_DIR/.venv/bin/python"
elif [[ -x "$ROOT_DIR/../shoonya_env/bin/python" ]]; then
  PYTHON_EXEC="$ROOT_DIR/../shoonya_env/bin/python"
else
  echo "❌ Error: Virtual environment not found (.venv or ../shoonya_env)"
  exit 1
fi

# Execute main.py with NFO exchange forced
echo "☀️ Starting Orbiter in NFO mode..."
"$PYTHON_EXEC" "$ROOT_DIR/orbiter/main.py" --exchange=nfo "$@"
