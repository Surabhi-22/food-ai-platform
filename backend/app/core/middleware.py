"""
Security hardening middleware and utilities.

Provides:
    - SecurityHeadersMiddleware: OWASP-recommended HTTP headers
    - RateLimitMiddleware: IP + token-based rate limiting via Redis
    - Vendor isolation assertion helper
    - CORS configuration helper

All middleware is designed to be plugged into FastAPI's middleware stack.
"""

import logging
import time
from typing import Optional
from uuid import UUID

from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app.core.config import get_settings
from app.core.redis import cache_get, cache_set, get_redis

logger = logging.getLogger(__name__)
settings = get_settings()

# ── Constants ────────────────────────────────────────────────────────────────

RATE_LIMIT_IP_MAX = 100          # requests per minute per IP
RATE_LIMIT_VENDOR_MAX = 60       # requests per minute per vendor token
RATE_LIMIT_WINDOW = 60           # seconds


# ── Security Headers Middleware ──────────────────────────────────────────────

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Inject OWASP-recommended security headers into every response.

    Headers added:
        - X-Content-Type-Options: nosniff
        - X-Frame-Options: DENY
        - X-XSS-Protection: 1; mode=block
        - Strict-Transport-Security (HSTS): 1 year
        - Referrer-Policy: strict-origin-when-cross-origin
        - Permissions-Policy: restricted camera/mic/geolocation
        - Cache-Control: no-store for API responses
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        response = await call_next(request)

        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=()"
        )

        # HSTS only in production (requires HTTPS)
        if settings.ENVIRONMENT == "production":
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )

        # Prevent caching of API responses
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
            response.headers["Pragma"] = "no-cache"

        return response


# ── Rate Limiting Middleware ─────────────────────────────────────────────────

class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Token-bucket rate limiting using Redis.

    Limits:
        - 100 req/min per IP address (anonymous + authenticated)
        - 60 req/min per vendor token (authenticated only)

    Returns 429 Too Many Requests with Retry-After header.
    """

    # Paths exempt from rate limiting
    EXEMPT_PATHS = {"/health", "/docs", "/openapi.json", "/redoc"}

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        path = request.url.path

        # Skip rate limiting for exempt paths and non-API routes
        if path in self.EXEMPT_PATHS or not path.startswith("/api/"):
            return await call_next(request)

        client_ip = self._get_client_ip(request)

        # IP-based rate limit
        ip_allowed, ip_count, ip_remaining = await self._check_limit(
            f"ratelimit:ip:{client_ip}", RATE_LIMIT_IP_MAX
        )
        if not ip_allowed:
            return self._rate_limit_response(ip_remaining)

        # Vendor-token rate limit (if authenticated)
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token_hash = str(hash(auth_header[7:]))[:16]
            vendor_allowed, _, vendor_remaining = await self._check_limit(
                f"ratelimit:vendor:{token_hash}", RATE_LIMIT_VENDOR_MAX
            )
            if not vendor_allowed:
                return self._rate_limit_response(vendor_remaining)

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(RATE_LIMIT_IP_MAX)
        response.headers["X-RateLimit-Remaining"] = str(ip_remaining)
        return response

    @staticmethod
    def _get_client_ip(request: Request) -> str:
        """Extract real client IP, respecting proxy headers."""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    @staticmethod
    async def _check_limit(key: str, max_req: int) -> tuple[bool, int, int]:
        """Increment counter and check against limit."""
        try:
            redis = await get_redis()
            pipe = redis.pipeline()
            pipe.incr(key)
            pipe.expire(key, RATE_LIMIT_WINDOW)
            results = await pipe.execute()
            count = results[0]
            remaining = max(0, max_req - count)
            return count <= max_req, count, remaining
        except Exception as e:
            logger.warning("Rate limit check failed: %s — allowing request", e)
            return True, 0, max_req

    @staticmethod
    def _rate_limit_response(remaining: int) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "success": False,
                "error": {
                    "code": "RATE_LIMIT_EXCEEDED",
                    "detail": "Too many requests. Please slow down.",
                },
            },
            headers={"Retry-After": str(RATE_LIMIT_WINDOW)},
        )


# ── Vendor Isolation Helper ─────────────────────────────────────────────────

def assert_vendor_ownership(
    resource_vendor_id: UUID,
    requesting_vendor_id: UUID,
    resource_name: str = "Resource",
) -> None:
    """
    Defense-in-depth vendor isolation check.

    Call this in every endpoint handler after fetching a resource from DB.
    Even if the SQL query filters by vendor_id, this double-checks
    that the resource belongs to the requesting vendor.

    Raises:
        HTTPException 403 if vendor IDs don't match.
    """
    if resource_vendor_id != requesting_vendor_id:
        from fastapi import HTTPException
        logger.warning(
            "Vendor isolation violation: %s vendor_id=%s accessed by vendor_id=%s",
            resource_name, resource_vendor_id, requesting_vendor_id,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied: this {resource_name} belongs to another vendor.",
        )


# ── CORS Configuration ──────────────────────────────────────────────────────

def configure_cors(app: FastAPI) -> None:
    """
    Configure CORS based on environment.

    - Development: allow localhost origins
    - Production: restrict to configured domains only
    """
    origins = settings.CORS_ORIGINS

    if settings.ENVIRONMENT == "production":
        # In production, only allow explicitly configured origins
        if not origins or origins == ["http://localhost:3000"]:
            logger.warning(
                "CORS_ORIGINS not configured for production! "
                "Set CORS_ORIGINS to your production domain."
            )
            origins = []

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
        allow_headers=["*"],
        expose_headers=["X-RateLimit-Limit", "X-RateLimit-Remaining"],
    )


# ── Register All Security Middleware ─────────────────────────────────────────

def register_security_middleware(app: FastAPI) -> None:
    """Register all security middleware in correct order."""
    # Order matters: outermost middleware runs first
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RateLimitMiddleware)
    configure_cors(app)
    logger.info("Security middleware registered: headers, rate-limit, CORS")
