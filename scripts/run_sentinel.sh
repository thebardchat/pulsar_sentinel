#!/bin/bash
# PULSAR SENTINEL - Server Run Script

set -e

# Default values
HOST="${API_HOST:-0.0.0.0}"
PORT="${API_PORT:-8000}"
WORKERS="${WORKERS:-1}"
LOG_LEVEL="${LOG_LEVEL:-info}"
RELOAD="${RELOAD:-false}"

echo "==================================="
echo "PULSAR SENTINEL Server"
echo "==================================="
echo "Host: $HOST"
echo "Port: $PORT"
echo "Workers: $WORKERS"
echo "Log Level: $LOG_LEVEL"
echo "==================================="

# Activate virtual environment if exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Change to src directory
cd "$(dirname "$0")/.."

# Run with uvicorn
if [ "$RELOAD" = "true" ]; then
    echo "Starting in development mode (with reload)..."
    uvicorn api.server:app \
        --host "$HOST" \
        --port "$PORT" \
        --log-level "$LOG_LEVEL" \
        --reload
else
    echo "Starting in production mode..."
    uvicorn api.server:app \
        --host "$HOST" \
        --port "$PORT" \
        --workers "$WORKERS" \
        --log-level "$LOG_LEVEL"
fi
