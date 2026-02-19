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

# 0. Pre-Release Test Suite
echo "🧪 Running mandatory pre-release tests..."
./run_tests.sh
if [ $? -ne 0 ]; then
    echo "❌ Tests failed. Release aborted."
    exit 1
fi

echo "📦 Preparing release: ${FULL_VERSION}"

# 1. Update version.txt
echo "${FULL_VERSION}" > version.txt

# 2. Update CHANGELOG.md (Add entry if not present)
if ! grep -q "## \[${FULL_VERSION}\]" CHANGELOG.md; then
    echo "📝 Adding entry to CHANGELOG.md..."
    # Add after header (line 3)
    sed -i '' "3i\\
## [${FULL_VERSION}] - $(date +%Y-%m-%d)\\
### Changed\\
- Automated release update.\\
" CHANGELOG.md
fi

# 3. Regenerate checksums.txt (MUST BE DONE AFTER VERSION UPDATES)
echo "🧮 Regenerating checksums.txt..."
find . -type f \( -name "*.py" -o -name "*.md" -o -name "*.json" -o -name "*.yml" -o -name "*.yaml" -o -name "Dockerfile" -o -name "*.sh" -o -name "*.service" -o -name "*.env" \) \
    -not -path "*/.*" \
    -not -path "./.venv/*" \
    -not -path "./shoonya_env/*" \
    -not -path "./python-trader/*" \
    -not -path "*/__pycache__/*" \
    -not -path "./logs/*" \
    -not -path "./orbiter/logs/*" \
    -not -path "./backtest_lab/data/*" \
    -not -path "./orbiter/data/span/*" \
    -not -path "./orbiter/data/nse_token_map.json" \
    -not -path "./checksums.txt" \
    -exec shasum -a 256 {} + | sed 's|  \./|  |' | sort > checksums.txt

echo "✅ Release ${FULL_VERSION} ready!"
echo "Files updated: version.txt, CHANGELOG.md, checksums.txt"
