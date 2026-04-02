#!/bin/sh
# Backend development startup script
# Syncs dependencies from requirements.txt on every start so you
# don't have to rebuild the container after adding a new package.

set -e

echo "Syncing Python dependencies..."
uv pip install --system -r requirements.txt 2>&1 | tail -5

echo "Starting uvicorn with hot-reload on port 8000..."
exec uvicorn main:app --reload --host 0.0.0.0 --port 8000
