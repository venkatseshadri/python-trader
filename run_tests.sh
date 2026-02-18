#!/bin/bash

# 🧪 ORBITER Test Runner
# Runs all local tests before release.

echo "🔍 Running Orbiter Test Suite..."

# 1. Run unit tests
export PYTHONPATH=$PYTHONPATH:$(pwd)/orbiter:$(pwd)/ShoonyaApi-py
./.venv/bin/python3 -m unittest discover -s orbiter/tests -p "test_*.py"

RESULT=$?

if [ $RESULT -eq 0 ]; then
    echo "✅ ALL TESTS PASSED!"
    exit 0
else
    echo "❌ TESTS FAILED! Aborting release."
    exit 1
fi
