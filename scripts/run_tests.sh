#!/usr/bin/env bash

# This script runs the full test suite for earnings-transcript-teacher.
# It can be run locally or in a CI/CD environment.

set -e # Exit immediately if a command exits with a non-zero status

echo "🏃 Running Pytest suite..."

if [ -f ".venv/bin/activate" ]; then
    echo "Activting virtual environment..."
    source .venv/bin/activate
fi

# Run tests with coverage reporting
# Exclude the DB persistence pass-through wrapper and main entry points from core unit testing coverage requirements
python -m pytest tests/ \
    -v \
    --cov=. \
    --cov-report=term-missing \
    --cov-report=xml \
    --cov-fail-under=60

echo "✅ All tests passed successfully!"
