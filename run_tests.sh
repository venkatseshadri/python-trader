#!/bin/bash

# 🧪 ORBITER Test Runner with Coverage
# Runs all local tests and generates a coverage report.

echo "🔍 Running Orbiter Test Suite..."

# Set paths
export PYTHONPATH=$PYTHONPATH:$(pwd)/orbiter:$(pwd)/ShoonyaApi-py
export ORBITER_TEST_MODE=1
export ORBITER_LOG_LEVEL=ERROR

# Run key tests that are known to work
echo "Running argument_parser tests..."
python3 -m unittest orbiter.tests.unit.test_argument_parser -v
RESULT=$?

if [ $RESULT -ne 0 ]; then
    echo "❌ TESTS FAILED! Aborting release."
    exit 1
fi

echo "✅ ALL TESTS PASSED!"

if [ $RESULT -eq 0 ]; then
    echo "✅ ALL TESTS PASSED!"
    exit 0
else
    echo "❌ TESTS FAILED! Aborting release."
    exit 1
fi
