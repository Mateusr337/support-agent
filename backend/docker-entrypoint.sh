#!/bin/sh
set -e

echo ""
echo "Support Agent API: http://localhost:8000"
echo "API docs:        http://localhost:8000/docs"
echo "Qdrant:          http://localhost:${QDRANT_HTTP_PORT:-6335}/dashboard"
echo ""

if [ "$1" = "uvicorn" ]; then
  alembic upgrade head
  workers="${UVICORN_WORKERS:-1}"
  if [ "$workers" -gt 1 ] 2>/dev/null; then
    exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers "$workers"
  fi
fi

exec "$@"
