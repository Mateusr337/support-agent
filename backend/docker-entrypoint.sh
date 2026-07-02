#!/bin/sh
set -e

echo ""
echo "Support Agent API: http://localhost:8000"
echo "API docs:        http://localhost:8000/docs"
echo "Qdrant:          http://localhost:${QDRANT_HTTP_PORT:-6335}/dashboard"
echo ""

exec "$@"
