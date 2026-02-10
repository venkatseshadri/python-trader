#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="$ROOT_DIR/.venv"

sudo apt-get update
sudo apt-get install -y \
  python3 \
  python3-venv \
  python3-pip \
  build-essential \
  libssl-dev \
  libffi-dev \
  libta-lib0 \
  libta-lib-dev

python3 -m venv "$VENV_DIR"
"$VENV_DIR/bin/pip" install --upgrade pip wheel

"$VENV_DIR/bin/pip" install -r "$ROOT_DIR/orbiter/requirements.txt"
"$VENV_DIR/bin/pip" install -r "$ROOT_DIR/ShoonyaApi-py/requirements.txt"

echo "Install complete. Activate with: source $VENV_DIR/bin/activate"
