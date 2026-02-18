#!/bin/bash

# 🚀 ORBITER Release Automation Script
# Updates version.txt, main.py, README, and regenerates checksums.

# Read current version base from version.txt (e.g. 3.2.1)
# If version.txt doesn't exist, default to 3.1.0
if [ -f "version.txt" ]; then
    VERSION_BASE=$(cat version.txt | cut -d'-' -f1)
else
    VERSION_BASE="3.1.0"
fi

DATE=$(date +%Y%m%d)
GIT_HASH=$(git rev-parse --short=7 HEAD)
FULL_VERSION="${VERSION_BASE}-${DATE}-${GIT_HASH}"

echo "📦 Preparing release: ${FULL_VERSION}"

# 1. Update version.txt
echo "${FULL_VERSION}" > version.txt

# 2. Update orbiter/main.py (Docstring + Variable)
# Using perl for cross-platform compatibility (macOS/Linux)
perl -i -pe "s/^VERSION = \".*?\"/VERSION = \"${FULL_VERSION}\"/g" orbiter/main.py
perl -i -pe "s/🚀 ORBITER v.*? -/🚀 ORBITER v${FULL_VERSION} -/g" orbiter/main.py

# 3. Update README.md
perl -i -pe "s/\*\*ORBITER v.*? \*\*/\*\*ORBITER v${FULL_VERSION} \*\*/g" orbiter/README.md
perl -i -pe "s/Version .*? -/Version ${FULL_VERSION} -/g" orbiter/README.md

# 4. Update CHANGELOG.md (Add entry if not present)
if ! grep -q "## \[${FULL_VERSION}\]" CHANGELOG.md; then
    echo "📝 Adding entry to CHANGELOG.md..."
    # Insert after the # Changelog header
    perl -i -pe "print \"## [${FULL_VERSION}] - $(date +%Y-%m-%d)\n### Changed\n- Auto-versioned release update.\n\n\" if $. == 3" CHANGELOG.md
fi

# 5. Regenerate checksums.txt
echo "🧮 Regenerating checksums.txt..."
# Use find to generate file list, then calculate shasum with relative paths
find . -type f \( -name "*.py" -o -name "*.md" -o -name "*.json" -o -name "*.yml" -o -name "*.yaml" -o -name "Dockerfile" -o -name "*.sh" -o -name "*.service" -o -name "*.env" \) \
    -not -path "*/.*" \
    -not -path "./.venv/*" \
    -not -path "./shoonya_env/*" \
    -not -path "*/__pycache__/*" \
    -not -path "./logs/*" \
    -not -path "./orbiter/logs/*" \
    -not -path "./checksums.txt" \
    -not -path "./version.txt" \
    -exec shasum -a 256 {} + | sed 's|  \./|  |' | sort > checksums.txt

echo "✅ Release ${FULL_VERSION} ready!"
echo "Files updated: version.txt, orbiter/main.py, orbiter/README.md, CHANGELOG.md, checksums.txt"
