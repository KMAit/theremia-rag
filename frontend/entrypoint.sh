#!/bin/sh
BACKEND_URL="${BACKEND_URL:-http://backend:8000}"
PORT="${PORT:-80}"

sed -i "s|BACKEND_URL_PLACEHOLDER|${BACKEND_URL}|g" /etc/nginx/conf.d/default.conf
sed -i "s|listen 80;|listen ${PORT};|g" /etc/nginx/conf.d/default.conf

echo "Backend URL set to: ${BACKEND_URL}"
echo "Listening on port: ${PORT}"
nginx -g "daemon off;"