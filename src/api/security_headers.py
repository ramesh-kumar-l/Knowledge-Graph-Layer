"""Security headers middleware — adds OWASP-recommended HTTP security headers.

CSP is omitted for /docs and /redoc paths so Swagger UI continues to load.
HSTS is only added over HTTPS (checked via request scheme).
"""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

_DOCS_PATHS = frozenset({"/docs", "/redoc", "/openapi.json", "/v1/openapi.json"})

_COMMON_HEADERS: dict[str, str] = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
}

_CSP = (
    "default-src 'none'; "
    "script-src 'self'; "
    "style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data:; "
    "connect-src 'self'; "
    "frame-ancestors 'none'"
)

_HSTS = "max-age=63072000; includeSubDomains; preload"


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to every response. CSP skipped for API doc paths."""

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        for header, value in _COMMON_HEADERS.items():
            response.headers[header] = value
        if request.url.path not in _DOCS_PATHS:
            response.headers["Content-Security-Policy"] = _CSP
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = _HSTS
        return response
