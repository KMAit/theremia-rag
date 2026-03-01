"""
Security middleware:
- Security headers on every response
- In-memory rate limiting (sliding window) for costly endpoints

Note: In production, replace in-memory limiter with Redis for multi-instance.
"""
import time
import logging
from collections import defaultdict
from typing import Callable

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings

logger = logging.getLogger("theremia.security")


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        # Avoid exposing server details
        response.headers["Server"] = "theremia"
        return response


class RateLimiter:
    def __init__(self):
        self._windows: dict[str, list[float]] = defaultdict(list)

    def is_allowed(self, key: str, max_requests: int, window_seconds: int) -> tuple[bool, int]:
        now = time.time()
        window_start = now - window_seconds
        hits = self._windows[key]

        # Purge old hits
        self._windows[key] = [t for t in hits if t > window_start]
        current = len(self._windows[key])

        if current >= max_requests:
            oldest = self._windows[key][0]
            retry_after = int(oldest + window_seconds - now) + 1
            return False, retry_after

        self._windows[key].append(now)
        return True, 0


_rate_limiter = RateLimiter()


def get_client_ip(request: Request) -> str:
    """
    If TRUST_PROXY_HEADERS=true, use X-Forwarded-For (assuming a trusted reverse proxy).
    Otherwise, use the direct client IP.
    """
    if getattr(settings, "TRUST_PROXY_HEADERS", False):
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()

    return request.client.host if request.client else "unknown"


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Applies different limits by endpoint:
    - POST .../messages (LLM calls): 20 req / minute
    - POST /documents (upload): 10 req / minute
    - Global: 120 req / minute
    """
    RULES = [
        ("/api/v1/conversations", "POST", "messages", 20, 60),  # only when path endswith /messages
        ("/api/v1/documents", "POST", "upload", 10, 60),
        ("/api/v1", "*", "global", 120, 60),
    ]

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path
        method = request.method
        ip = get_client_ip(request)

        for prefix, rule_method, name, limit, window in self.RULES:
            if not path.startswith(prefix):
                continue
            if not (rule_method == "*" or method == rule_method):
                continue

            # Make the "messages" rule precise (avoid rate-limiting POST /conversations)
            if name == "messages" and not path.endswith("/messages"):
                continue

            key = f"{ip}:{name}"
            allowed, retry_after = _rate_limiter.is_allowed(key, limit, window)
            if not allowed:
                logger.warning(f"Rate limit exceeded: ip={ip} rule={name}")
                return JSONResponse(
                    status_code=429,
                    content={
                        "error": "Too many requests",
                        "detail": f"Limit: {limit} requests per {window}s. Retry in {retry_after}s.",
                    },
                    headers={"Retry-After": str(retry_after)},
                )
            break

        return await call_next(request)


def register_security_middleware(app: FastAPI) -> None:
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RateLimitMiddleware)
