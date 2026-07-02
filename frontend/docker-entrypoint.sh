#!/bin/sh
set -e

echo ""
echo "Support Agent frontend: http://localhost:5173"
echo "API URL: ${VITE_API_URL:-http://localhost:8000}"
echo ""

exec "$@"
