#!/usr/bin/env bash
# Starts a local dev server with HTTP Range (byte-serving) support.
# Required for PMTiles vector tile loading in the completeness map.
#
# Usage:  ./serve.sh [port]   (default port: 8080)
PORT="${1:-8080}"
echo "Starting http-server on port $PORT (Range-requests enabled)..."
npx --yes http-server -p "$PORT" --cors -c-1
