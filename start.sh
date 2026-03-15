#!/usr/bin/env bash
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if command -v python3 &>/dev/null; then
    python3 start.py
elif python --version 2>&1 | grep -q "^Python 3"; then
    python start.py
else
    echo "Python 3 not found. Install from https://python.org"
    exit 1
fi
