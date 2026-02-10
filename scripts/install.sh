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
if [[ ! -f /lib/libta_lib.so && ! -f /usr/lib/libta_lib.so && ! -f /usr/lib/aarch64-linux-gnu/libta_lib.so && ! -f /usr/local/lib/libta_lib.so ]]; then
  mkdir -p /tmp/ta-lib-build
  cd /tmp/ta-lib-build
  wget -q https://sourceforge.net/projects/ta-lib/files/ta-lib/0.4.0/ta-lib-0.4.0-src.tar.gz
  tar -xzf ta-lib-0.4.0-src.tar.gz
  cd ta-lib
  # Refresh config.guess/config.sub for newer ARM platforms
  wget -q -O config.guess "https://git.savannah.gnu.org/cgit/config.git/plain/config.guess"
  wget -q -O config.sub "https://git.savannah.gnu.org/cgit/config.git/plain/config.sub"
  chmod +x config.guess config.sub
  ./configure --prefix=/usr
  make
  sudo make install
  sudo ldconfig
  cd /
  rm -rf /tmp/ta-lib-build
fi

python3 -m venv "$VENV_DIR"
"$VENV_DIR/bin/pip" install --upgrade pip wheel

"$VENV_DIR/bin/pip" install -r "$ROOT_DIR/orbiter/requirements.txt"
"$VENV_DIR/bin/pip" install "$ROOT_DIR/ShoonyaApi-py/dist/NorenRestApi-0.0.30-py2.py3-none-any.whl"

echo "Install complete. Activate with: source $VENV_DIR/bin/activate"
