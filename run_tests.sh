#!/bin/bash

# 🧪 ORBITER Test Runner with Coverage
# Runs all local tests and generates a coverage report.

echo "🔍 Running Orbiter Test Suite..."

# Set paths
export PYTHONPATH=$PYTHONPATH:$(pwd)/orbiter:$(pwd)/ShoonyaApi-py

# 1. Run unit tests with coverage
./.venv/bin/python3 -m coverage run --source=orbiter/core -m unittest discover -s orbiter/tests -p "test_*.py"

RESULT=$?

# 2. Generate Report
./.venv/bin/python3 -m coverage report -m

if [ $RESULT -eq 0 ]; then
    echo "✅ ALL TESTS PASSED!"
    exit 0
else
    echo "❌ TESTS FAILED! Aborting release."
    exit 1
fi
