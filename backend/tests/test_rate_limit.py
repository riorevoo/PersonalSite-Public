from fastapi.testclient import TestClient
from starlette.types import Scope

from app.core.config import Settings
from app.core.rate_limit import RATE_LIMIT_DETAIL, RateLimiter, Rule, client_ip
from app.main import create_app


class FakeClock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def make(*rules: Rule, max_keys: int = 10_000) -> tuple[RateLimiter, FakeClock]:
    clock = FakeClock()
    return RateLimiter(rules, clock=clock, max_keys=max_keys), clock


class TestRateLimiter:
    def test_allows_up_to_the_limit_then_blocks(self) -> None:
        limiter, _ = make(Rule(limit=3, window_seconds=60))

        assert [limiter.check("a").allowed for _ in range(3)] == [True, True, True]
        blocked = limiter.check("a")

        assert blocked.allowed is False
        assert blocked.retry_after > 0

    def test_tells_the_visitor_when_a_slot_frees(self) -> None:
        limiter, clock = make(Rule(limit=2, window_seconds=60))
        limiter.check("a")  # t=0
        clock.advance(10)
        limiter.check("a")  # t=10
        clock.advance(10)  # t=20; the first request expires at t=60

        assert limiter.check("a").retry_after == 40

    def test_the_window_slides(self) -> None:
        limiter, clock = make(Rule(limit=1, window_seconds=60))
        assert limiter.check("a").allowed
        assert not limiter.check("a").allowed

        clock.advance(60.1)

        assert limiter.check("a").allowed

    def test_blocked_requests_do_not_extend_the_wait(self) -> None:
        limiter, clock = make(Rule(limit=1, window_seconds=60))
        limiter.check("a")
        for _ in range(5):
            clock.advance(5)
            assert not limiter.check("a").allowed

        clock.advance(35.1)  # 60.1s after the only request that counted

        assert limiter.check("a").allowed

    def test_each_address_is_counted_separately(self) -> None:
        limiter, _ = make(Rule(limit=1, window_seconds=60))
        assert limiter.check("a").allowed
        assert not limiter.check("a").allowed
        assert limiter.check("b").allowed

    def test_every_rule_applies(self) -> None:
        limiter, clock = make(Rule(limit=2, window_seconds=60), Rule(limit=3, window_seconds=3600))
        assert limiter.check("a").allowed
        assert limiter.check("a").allowed
        assert not limiter.check("a").allowed  # per-minute rule

        clock.advance(61)
        assert limiter.check("a").allowed  # third of the hour
        clock.advance(61)
        hourly = limiter.check("a")  # per-hour rule now blocks

        assert not hourly.allowed
        assert hourly.retry_after > 3000

    def test_retry_after_is_at_least_one_second(self) -> None:
        limiter, clock = make(Rule(limit=1, window_seconds=60))
        limiter.check("a")
        clock.advance(59.9999)

        assert limiter.check("a").retry_after == 1

    def test_memory_is_bounded_by_dropping_the_least_recently_seen_address(self) -> None:
        limiter, _ = make(Rule(limit=1, window_seconds=60), max_keys=3)
        for key in ("a", "b", "c"):
            limiter.check(key)
        limiter.check("b")  # refresh b, so a is now the least recently seen
        limiter.check("d")  # evicts a

        assert limiter.check("a").allowed  # a was forgotten, so it starts fresh
        assert not limiter.check("d").allowed  # d is still remembered


def scope_with(peer: str | None, forwarded: str | None = None) -> Scope:
    headers = [(b"x-forwarded-for", forwarded.encode())] if forwarded is not None else []
    return {"type": "http", "client": (peer, 1234) if peer else None, "headers": headers}


class TestClientIp:
    def test_uses_the_connection_address_by_default(self) -> None:
        assert client_ip(scope_with("10.0.0.1", "1.1.1.1"), trusted_hops=0) == "10.0.0.1"

    def test_reads_the_address_the_trusted_proxy_appended(self) -> None:
        scope = scope_with("10.0.0.1", "203.0.113.9")
        assert client_ip(scope, trusted_hops=1) == "203.0.113.9"

    def test_ignores_addresses_a_visitor_put_in_front_of_the_real_one(self) -> None:
        # The visitor claimed to be 1.1.1.1; the proxy appended who it really was.
        scope = scope_with("10.0.0.1", "1.1.1.1, 203.0.113.9")
        assert client_ip(scope, trusted_hops=1) == "203.0.113.9"

    def test_counts_hops_from_the_right(self) -> None:
        scope = scope_with("10.0.0.1", "1.1.1.1, 203.0.113.9, 172.16.0.5")
        assert client_ip(scope, trusted_hops=2) == "203.0.113.9"

    def test_falls_back_to_the_connection_when_the_chain_is_too_short(self) -> None:
        assert client_ip(scope_with("10.0.0.1", "203.0.113.9"), trusted_hops=2) == "10.0.0.1"
        assert client_ip(scope_with("10.0.0.1"), trusted_hops=1) == "10.0.0.1"
        assert client_ip(scope_with("10.0.0.1", " , "), trusted_hops=1) == "10.0.0.1"

    def test_copes_with_no_connection_info(self) -> None:
        assert client_ip(scope_with(None), trusted_hops=0) == "unknown"


def chat(client: TestClient, message: str = "what experience do you have?") -> int:
    return client.post("/api/chat", json={"message": message}).status_code


class TestChatEndpointLimit:
    def test_blocks_after_the_limit_with_a_helpful_response(self) -> None:
        client = TestClient(create_app(Settings(rate_limit_per_minute=2)))
        assert [chat(client), chat(client)] == [200, 200]

        response = client.post("/api/chat", json={"message": "hi"})

        assert response.status_code == 429
        assert response.json() == {"detail": RATE_LIMIT_DETAIL}
        assert int(response.headers["Retry-After"]) >= 1
        assert response.headers["X-Request-ID"]

    def test_the_daily_limit_applies_too(self) -> None:
        settings = Settings(rate_limit_per_minute=50, rate_limit_per_day=3)
        client = TestClient(create_app(settings))

        assert [chat(client) for _ in range(4)] == [200, 200, 200, 429]

    def test_other_endpoints_are_not_limited(self) -> None:
        client = TestClient(create_app(Settings(rate_limit_per_minute=1)))
        assert all(client.get("/api/health").status_code == 200 for _ in range(20))

    def test_each_visitor_has_their_own_allowance(self) -> None:
        app = create_app(Settings(rate_limit_per_minute=1))
        first = TestClient(app, client=("198.51.100.1", 1000))
        second = TestClient(app, client=("198.51.100.2", 1000))

        assert chat(first) == 200
        assert chat(first) == 429
        assert chat(second) == 200

    def test_blocked_requests_are_rejected_before_the_body_is_parsed(self) -> None:
        client = TestClient(create_app(Settings(rate_limit_per_minute=1)))

        def post_garbage() -> int:
            headers = {"Content-Type": "application/json"}
            return client.post("/api/chat", content=b"{not json", headers=headers).status_code

        assert post_garbage() == 422  # counted
        assert post_garbage() == 429  # not parsed at all

    def test_a_429_is_readable_by_the_allowed_browser_origin(self) -> None:
        settings = Settings(rate_limit_per_minute=1, cors_origins=["https://site.example"])
        client = TestClient(create_app(settings))
        headers = {"Origin": "https://site.example"}
        client.post("/api/chat", json={"message": "hi"}, headers=headers)

        blocked = client.post("/api/chat", json={"message": "hi"}, headers=headers)

        assert blocked.status_code == 429
        assert blocked.headers["access-control-allow-origin"] == "https://site.example"

    def test_behind_a_proxy_visitors_are_told_apart_by_forwarded_address(self) -> None:
        settings = Settings(rate_limit_per_minute=1, trusted_proxy_hops=1)
        client = TestClient(create_app(settings))

        def ask(forwarded: str) -> int:
            body = {"message": "hi"}
            return client.post(
                "/api/chat", json=body, headers={"X-Forwarded-For": forwarded}
            ).status_code

        assert ask("203.0.113.1") == 200
        assert ask("203.0.113.1") == 429
        assert ask("203.0.113.2") == 200  # a different visitor, same proxy

    def test_a_visitor_cannot_dodge_the_limit_by_faking_the_header(self) -> None:
        settings = Settings(rate_limit_per_minute=1, trusted_proxy_hops=1)
        client = TestClient(create_app(settings))

        def ask(faked: str) -> int:
            # A real proxy appends the true address, which here is always 203.0.113.7.
            header = f"{faked}, 203.0.113.7"
            return client.post(
                "/api/chat", json={"message": "hi"}, headers={"X-Forwarded-For": header}
            ).status_code

        assert ask("1.1.1.1") == 200
        assert ask("2.2.2.2") == 429
