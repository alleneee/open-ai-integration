#!/bin/zsh

# Exit immediately if a command exits with a non-zero status.
set -e

# Define default host and port, allowing overrides via environment variables
HOST=${HOST:-0.0.0.0} # Listens on all available network interfaces
PORT=${PORT:-8000} # Standard development port

echo "Starting FastAPI backend in development mode..."
echo "Access URL: http://${HOST}:${PORT}"
echo "Using Host: ${HOST}"
echo "Using Port: ${PORT}"
echo "Auto-reload enabled. Press CTRL+C to stop."

# Run Uvicorn
# - app.main:app -> Points to the FastAPI app instance in app/main.py
# - --host -> Specifies the host IP address
# - --port -> Specifies the port number
# - --reload -> Enables auto-reloading when code changes are detected
uvicorn app.main:app --host "$HOST" --port "$PORT" --reload

echo "Backend stopped." 