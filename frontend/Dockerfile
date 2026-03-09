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

# Copy nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy entrypoint script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 80

HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
    CMD wget -qO- http://localhost/ || exit 1

# Entrypoint adjusts port at startup
ENTRYPOINT ["/entrypoint.sh"]