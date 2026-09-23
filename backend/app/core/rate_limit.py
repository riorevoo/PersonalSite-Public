"""Per-visitor rate limiting for the chat endpoint.

A sliding-window log per client address, held in memory. That is exact and simple, and right for a
single-process deployment (a free-tier host runs one). If the app ever runs several workers, each
enforces its own limit; move the counters to a shared store then.
"""

import math
import time
from collections import OrderedDict, deque
from collections.abc import Callable, Iterable
from dataclasses import dataclass

from starlette.datastructures import Headers
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

RATE_LIMIT_DETAIL = "Too many questions. Please wait a moment and try again."


@dataclass(frozen=True)
class Rule:
    limit: int
    window_seconds: float


@dataclass(frozen=True)
class Decision:
    allowed: bool
    retry_after: int = 0  # whole seconds until a request would be allowed again


class RateLimiter:
    def __init__(
        self,
        rules: Iterable[Rule],
        *,
        clock: Callable[[], float] = time.monotonic,
        max_keys: int = 10_000,
    ) -> None:
        self._rules = tuple(rules)
        self._clock = clock
        self._max_keys = max_keys
        self._longest = max(rule.window_seconds for rule in self._rules)
        # Least recently seen addresses are dropped first, so memory stays bounded.
        self._hits: OrderedDict[str, deque[float]] = OrderedDict()

    def check(self, key: str) -> Decision:
        """Record a request from `key` if it is within every rule; otherwise say when to retry."""
        now = self._clock()
        hits = self._hits.setdefault(key, deque())
        self._hits.move_to_end(key)
        while hits and hits[0] <= now - self._longest:
            hits.popleft()

        retry_after = 0
        for rule in self._rules:
            recent = [t for t in hits if t > now - rule.window_seconds]
            if len(recent) >= rule.limit:
                # A slot frees when the oldest request still counted against this rule expires.
                frees_at = recent[len(recent) - rule.limit] + rule.window_seconds
                retry_after = max(retry_after, math.ceil(frees_at - now))
        if retry_after:
            return Decision(allowed=False, retry_after=max(retry_after, 1))

        hits.append(now)
        while len(self._hits) > self._max_keys:
            self._hits.popitem(last=False)
        return Decision(allowed=True)


def client_ip(scope: Scope, trusted_hops: int) -> str:
    """The visitor's address.

    Each trusted reverse proxy appends the address it received the request from to
    X-Forwarded-For, so the real client is `trusted_hops` entries from the right. Anything a client
    put further left is ignored, which is what stops a visitor spoofing their address.
    """
    peer = scope.get("client")
    direct = peer[0] if peer else "unknown"
    if trusted_hops <= 0:
        return direct
    forwarded = Headers(scope=scope).get("x-forwarded-for", "")
    chain = [part.strip() for part in forwarded.split(",") if part.strip()]
    return chain[-trusted_hops] if len(chain) >= trusted_hops else direct


class RateLimitMiddleware:
    """Answers 429 before the request body is read, so rejected requests cost almost nothing."""

    def __init__(
        self,
        app: ASGIApp,
        *,
        limiter: RateLimiter,
        trusted_proxy_hops: int = 0,
        paths: Iterable[str] = ("/api/chat",),
    ) -> None:
        self.app = app
        self.limiter = limiter
        self.trusted_proxy_hops = trusted_proxy_hops
        self.paths = frozenset(paths)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["method"] != "POST" or scope["path"] not in self.paths:
            await self.app(scope, receive, send)
            return

        decision = self.limiter.check(client_ip(scope, self.trusted_proxy_hops))
        if decision.allowed:
            await self.app(scope, receive, send)
            return

        scope.setdefault("state", {}).setdefault("log_fields", {})["rate_limited"] = True
        response = JSONResponse(
            {"detail": RATE_LIMIT_DETAIL},
            status_code=429,
            headers={"Retry-After": str(decision.retry_after)},
        )
        await response(scope, receive, send)
