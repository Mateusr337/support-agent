#!/bin/sh
set -e

echo ""
echo "Support Agent frontend: http://localhost:5173"
echo "API URL: ${VITE_API_URL}"
echo ""

exec "$@"
