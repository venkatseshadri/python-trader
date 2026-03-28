#!/bin/bash
# ============================================
# 🏗️ Orbiter Build Script
# Creates standalone binary using PyInstaller
# ============================================

set -e

# Config
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DIST_DIR="$PROJECT_ROOT/dist"
BUILD_DIR="$PROJECT_ROOT/build"
NAME="orbiter"

echo "🏗️  Building $NAME binary..."

# Clean previous builds
rm -rf "$DIST_DIR" "$BUILD_DIR"

# Build with PyInstaller
# --onefile: Single executable
# --name: Binary name
# --collect-all: Include all orbiter submodules
pyinstaller \
    --onefile \
    --name "$NAME" \
    --add-data "$PROJECT_ROOT:orbiter" \
    --collect-all orbiter \
    --hidden-import orbiter.utils.version \
    --hidden-import orbiter.utils.system \
    --hidden-import orbiter.utils.logger \
    --hidden-import orbiter.utils.lock \
    --hidden-import orbiter.core.app \
    "$PROJECT_ROOT/main.py"

# Get version
VERSION=$(python3 -c "from orbiter.utils.version import load_version; print(load_version('$PROJECT_ROOT'))")

# Rename with version
if [ -f "$DIST_DIR/$NAME" ]; then
    mv "$DIST_DIR/$NAME" "$DIST_DIR/${NAME}-${VERSION}"
    echo "✅ Built: $DIST_DIR/${NAME}-${VERSION}"
fi

echo "✅ Build complete!"
