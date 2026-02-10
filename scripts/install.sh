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
  wget

# Build TA-Lib from source (apt packages may be unavailable on Pi)
if ! ldconfig -p | grep -q libta_lib; then
  mkdir -p /tmp/ta-lib-build
  cd /tmp/ta-lib-build
  wget -q https://sourceforge.net/projects/ta-lib/files/ta-lib/0.4.0/ta-lib-0.4.0-src.tar.gz
  tar -xzf ta-lib-0.4.0-src.tar.gz
  cd ta-lib
  ./configure --prefix=/usr
  make
  sudo make install
  cd /
  rm -rf /tmp/ta-lib-build
fi

python3 -m venv "$VENV_DIR"
"$VENV_DIR/bin/pip" install --upgrade pip wheel

"$VENV_DIR/bin/pip" install -r "$ROOT_DIR/orbiter/requirements.txt"
"$VENV_DIR/bin/pip" install -r "$ROOT_DIR/ShoonyaApi-py/requirements.txt"

echo "Install complete. Activate with: source $VENV_DIR/bin/activate"
