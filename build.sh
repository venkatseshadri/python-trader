#!/bin/bash
# ============================================
# 🏗️ Orbiter Build Script for CI/CD
# Creates standalone binary using PyInstaller
# ============================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "🏗️  Building Orbiter binary..."

# Clean previous builds
rm -rf dist build *.spec

# Build with PyInstaller
pyinstaller \
    --onefile \
    --name "orbiter" \
    --paths . \
    --paths ./ShoonyaApi-py \
    --add-data "version.txt:." \
    --add-data "manifest.json:." \
    --hidden-import orbiter.utils.version \
    --hidden-import orbiter.utils.system \
    --hidden-import orbiter.utils.logger \
    --hidden-import orbiter.utils.lock \
    --hidden-import orbiter.utils.argument_parser \
    --hidden-import orbiter.core.app \
    --hidden-import talib \
    --hidden-import talib.stream \
    --hidden-import talib._ta_lib \
    --hidden-import api_helper \
    --hidden-import api_helper.ShoonyaApiPy \
    orbiter/main.py

# Get version from the binary
VERSION=$(./dist/orbiter --version | awk '{print $2}')

# Rename with version
mv dist/orbiter "dist/orbiter-${VERSION}"

# Generate checksums
cd dist
sha256sum "orbiter-${VERSION}" > "orbiter-${VERSION}.sha256"
cat "orbiter-${VERSION}.sha256"

echo ""
echo "✅ Build complete!"
echo "   Binary: dist/orbiter-${VERSION}"
echo "   Size: $(du -h "orbiter-${VERSION}" | cut -f1)"
