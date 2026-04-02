#!/bin/sh
# Frontend development startup script
# Syncs dependencies from package.json on every start so you
# don't have to rebuild the container after adding a new package.

set -e

echo "Syncing Node dependencies..."
pnpm install 2>&1 | tail -5

echo "Starting Next.js dev server on port 4000..."
exec pnpm dev --hostname 0.0.0.0 --port 4000
