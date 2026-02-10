#!/usr/bin/env bash
set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/venkatseshadri/python-trader.git}"
TARGET_DIR="${TARGET_DIR:-python-trader}"

if [[ -d "$TARGET_DIR/.git" ]]; then
  echo "Updating existing repo in $TARGET_DIR"
  git -C "$TARGET_DIR" pull
else
  echo "Cloning $REPO_URL into $TARGET_DIR"
  git clone "$REPO_URL" "$TARGET_DIR"
fi

cd "$TARGET_DIR"
./scripts/install.sh

echo "Bootstrap complete. Run with: ./scripts/run.sh"
