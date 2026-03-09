#!/bin/sh
BACKEND_URL="${BACKEND_URL:-http://backend:8000}"
PORT="${PORT:-80}"

# Extract host from BACKEND_URL (remove https:// or http://)
BACKEND_HOST=$(echo "$BACKEND_URL" | sed 's|https\?://||')

sed -i "s|BACKEND_URL_PLACEHOLDER|${BACKEND_URL}|g" /etc/nginx/conf.d/default.conf
sed -i "s|HOST_PLACEHOLDER|${BACKEND_HOST}|g" /etc/nginx/conf.d/default.conf
sed -i "s|listen 80;|listen ${PORT};|g" /etc/nginx/conf.d/default.conf

echo "Backend URL set to: ${BACKEND_URL}"
echo "Backend Host set to: ${BACKEND_HOST}"
echo "Listening on port: ${PORT}"
nginx -g "daemon off;"