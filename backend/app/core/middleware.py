"""ASGI middleware: request size cap, security headers and request logging.

Written as plain ASGI (not BaseHTTPMiddleware) so they work with any response and add no overhead.
"""

import logging
import re
import time
import uuid

from fastapi import HTTPException
from starlette.datastructures import Headers, MutableHeaders
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

access_logger = logging.getLogger("app.access")

_VALID_REQUEST_ID = re.compile(r"[A-Za-z0-9._-]{1,64}")


def _forwarded_entries(scope: Scope) -> int:
    header = Headers(scope=scope).get("x-forwarded-for", "")
    return sum(1 for part in header.split(",") if part.strip())


TOO_LARGE_DETAIL = "Request body is too large."


class BodySizeLimitMiddleware:
    """Rejects oversized request bodies with 413 before they are buffered.

    A declared Content-Length is checked up front. Bodies sent without one (chunked) are counted
    as they arrive, so a client cannot stream an unbounded payload into memory.
    """

    def __init__(self, app: ASGIApp, *, max_bytes: int) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        declared = Headers(scope=scope).get("content-length")
        if declared and declared.isdigit() and int(declared) > self.max_bytes:
            response = JSONResponse({"detail": TOO_LARGE_DETAIL}, status_code=413)
            await response(scope, receive, send)
            return

        received = 0

        async def limited_receive() -> Message:
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self.max_bytes:
                    # FastAPI re-raises HTTPException while reading a body, so this becomes a 413.
                    raise HTTPException(status_code=413, detail=TOO_LARGE_DETAIL)
            return message

        await self.app(scope, limited_receive, send)


class SecurityHeadersMiddleware:
    """Conservative headers for a JSON API. HSTS is only sent in production (over HTTPS)."""

    def __init__(self, app: ASGIApp, *, hsts: bool = False) -> None:
        self.app = app
        self.hsts = hsts

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        is_api = scope["path"].startswith("/api/")

        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                headers.setdefault("X-Content-Type-Options", "nosniff")
                headers.setdefault("Referrer-Policy", "no-referrer")
                headers.setdefault("Cache-Control", "no-store")
                if is_api:
                    # JSON only: nothing may be loaded or framed from an API response. Not applied
                    # to the /docs page, which needs scripts.
                    headers.setdefault(
                        "Content-Security-Policy", "default-src 'none'; frame-ancestors 'none'"
                    )
                if self.hsts:
                    headers.setdefault("Strict-Transport-Security", "max-age=63072000")
            await send(message)

        await self.app(scope, receive, send_with_headers)


class RequestLoggingMiddleware:
    """One structured log line per request, with a request id echoed in X-Request-ID.

    It logs method, path, status and timing, plus fields a route adds to `log_fields`. It never
    logs what a visitor typed.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        supplied = Headers(scope=scope).get("x-request-id", "")
        request_id = supplied if _VALID_REQUEST_ID.fullmatch(supplied) else uuid.uuid4().hex
        state = scope.setdefault("state", {})
        state["request_id"] = request_id
        status = 500  # what the client gets if the app fails before it starts a response

        async def send_with_request_id(message: Message) -> None:
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
                MutableHeaders(scope=message)["X-Request-ID"] = request_id
            await send(message)

        started = time.perf_counter()
        try:
            await self.app(scope, receive, send_with_request_id)
        finally:
            fields = {
                "request_id": request_id,
                "method": scope["method"],
                "path": scope["path"],
                "status": status,
                "duration_ms": round((time.perf_counter() - started) * 1000, 1),
                # How many addresses X-Forwarded-For carries (a count, never the addresses). Send a
                # request with one made-up address through the live site: proxies = count - 1, which
                # is what APP_TRUSTED_PROXY_HOPS must be.
                "forwarded_entries": _forwarded_entries(scope),
                **state.get("log_fields", {}),
            }
            quiet = scope["path"] == "/api/health"
            access_logger.log(logging.DEBUG if quiet else logging.INFO, "request", extra=fields)
