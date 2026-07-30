#!/bin/bash
# Simple launcher
set -e
cd "$(dirname "$0")/backend"
export PORT="${PORT:-8080}"
export HOST="${HOST:-0.0.0.0}"
echo "Starting LASTMA Portal on port $PORT …"
exec python3 main.py
