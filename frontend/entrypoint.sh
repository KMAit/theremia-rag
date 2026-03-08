#!/bin/sh
# Inject BACKEND_URL into nginx config at container startup
# Local Docker: BACKEND_URL defaults to http://backend:8000
# Railway:      BACKEND_URL set to https://your-backend.railway.app

BACKEND_URL="${BACKEND_URL:-http://backend:8000}"

sed -i "s|BACKEND_URL_PLACEHOLDER|${BACKEND_URL}|g" /etc/nginx/conf.d/default.conf

echo "Backend URL set to: ${BACKEND_URL}"

nginx -g "daemon off;"
