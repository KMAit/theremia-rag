# ── Stage 1: Builder ──────────────────────────────────────────────────────────
FROM node:20-alpine AS builder

WORKDIR /app

# Copy package files first to leverage Docker layer cache
COPY package.json package-lock.json ./

# Install dependencies (ci = strict install from lockfile)
RUN npm ci --ignore-scripts

# Copy source code
COPY . .

# Production build
RUN npm run build


# ── Stage 2: Runtime Nginx ────────────────────────────────────────────────────
FROM nginx:1.27-alpine AS runtime

# Security: remove default nginx config
RUN rm -rf /etc/nginx/conf.d/*

# Copy built assets
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy entrypoint script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Custom secure nginx config with placeholder for backend URL
RUN cat > /etc/nginx/conf.d/default.conf << 'NGINXEOF'
server {
    listen 80;
    server_name _;
    root /usr/share/nginx/html;
    index index.html;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # Gzip compression
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml image/svg+xml;
    gzip_min_length 1000;

    # Proxy API calls to backend — URL injected at startup via entrypoint.sh
    location /api/ {
        proxy_pass BACKEND_URL_PLACEHOLDER;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 300s;
        proxy_connect_timeout 10s;
        proxy_send_timeout 300s;
    }

    # SPA fallback — all routes return index.html
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Static assets: long-term cache
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
        access_log off;
    }

    # No logs for favicon/robots
    location = /favicon.ico { access_log off; log_not_found off; }
    location = /robots.txt  { access_log off; log_not_found off; }
}
NGINXEOF

EXPOSE 80

HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
    CMD wget -qO- http://localhost/ || exit 1

# Entrypoint injects BACKEND_URL at startup
ENTRYPOINT ["/entrypoint.sh"]