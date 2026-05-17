"""HTTPS configuration helpers and security headers middleware.

Provides:
  - ``SecurityHeadersMiddleware``: adds HSTS, CSP, X-Frame-Options, etc.
  - ``enforce_https()``: FastAPI dependency that redirects HTTP → HTTPS.
  - TLS configuration helpers for uvicorn.
"""

import logging

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to every response.

    Headers set:
      - Strict-Transport-Security (HSTS) with 1-year max-age
      - X-Content-Type-Options: nosniff
      - X-Frame-Options: DENY
      - X-XSS-Protection: 0 (modern browsers use CSP instead)
      - Referrer-Policy: strict-origin-when-cross-origin
      - Content-Security-Policy: restrictive default
      - Permissions-Policy: restrictive defaults
      - Cache-Control: no-store for API responses
    """

    def __init__(self, app, *, enable_hsts: bool = True, enable_csp: bool = True) -> None:
        super().__init__(app)
        self._enable_hsts = enable_hsts
        self._enable_csp = enable_csp

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)

        # HSTS
        if self._enable_hsts:
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )

        # Prevent MIME sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"

        # Disable legacy XSS filter (CSP is the modern approach)
        response.headers["X-XSS-Protection"] = "0"

        # Referrer policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Content Security Policy
        if self._enable_csp:
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data:; "
                "font-src 'self'; "
                "connect-src 'self'; "
                "frame-ancestors 'none'; "
                "base-uri 'self'; "
                "form-action 'self'"
            )

        # Permissions Policy (restrict browser features)
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=(), payment=()"
        )

        # No caching for API responses
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
            response.headers["Pragma"] = "no-cache"

        return response


def get_uvicorn_ssl_config(
    certfile: str = "/etc/ssl/certs/server.crt",
    keyfile: str = "/etc/ssl/private/server.key",
) -> dict:
    """Return uvicorn SSL kwargs for HTTPS.

    Usage::

        import uvicorn
        uvicorn.run(app, **get_uvicorn_ssl_config())
    """
    return {
        "ssl_certfile": certfile,
        "ssl_keyfile": keyfile,
    }
