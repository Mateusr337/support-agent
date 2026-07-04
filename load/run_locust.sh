#!/usr/bin/env bash
# Start the backend with load-test overrides and run Locust.
#
# Usage:
#   ./load/run_locust.sh --headless -u 50 -r 5 -t 5m
#   ./load/run_locust.sh --processes 4 --headless -u 100 -r 10 -t 3m
#
# Requires: docker compose, locust on PATH (or activate load/.venv first).

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "[load] Starting backend (LOAD_TEST=true, workers=${UVICORN_WORKERS:-4})..."
LOAD_TEST=true UVICORN_WORKERS="${UVICORN_WORKERS:-4}" docker compose up -d --build backend

echo "[load] Waiting for API health..."
for _ in $(seq 1 30); do
  if curl -sf "http://localhost:8000/api/v1/health" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

if ! curl -sf "http://localhost:8000/api/v1/health" >/dev/null 2>&1; then
  echo "[load] ERROR: API not healthy at http://localhost:8000"
  exit 1
fi

echo "[load] Running Locust (pass extra args after script name)..."
exec locust -f load/locustfile.py --host http://localhost:8000 "$@"
