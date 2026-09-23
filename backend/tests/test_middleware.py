import asyncio
import logging
import re
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from starlette.types import Message, Receive, Scope, Send

from app.core.config import Settings
from app.core.middleware import TOO_LARGE_DETAIL, BodySizeLimitMiddleware
from app.main import create_app

PRODUCTION = Settings(env="production", cors_origins=["https://site.example"])


class TestNonRequestTraffic:
    def test_server_lifecycle_events_pass_through_every_middleware(self) -> None:
        # Entering the client as a context manager runs the ASGI lifespan (a non-http scope).
        with TestClient(create_app()) as client:
            assert client.get("/api/health").status_code == 200

    def test_the_body_limit_ignores_messages_that_carry_no_body(self) -> None:
        seen: list[str] = []

        async def inner(scope: Scope, receive: Receive, send: Send) -> None:
            seen.append((await receive())["type"])

        async def receive() -> Message:
            return {"type": "http.disconnect"}

        async def send(message: Message) -> None:  # pragma: no cover - never responds
            raise AssertionError(message)

        middleware = BodySizeLimitMiddleware(inner, max_bytes=10)
        asyncio.run(middleware({"type": "http", "headers": []}, receive, send))

        assert seen == ["http.disconnect"]


class TestBodySizeLimit:
    def test_rejects_a_body_declared_larger_than_the_limit(self) -> None:
        client = TestClient(create_app(Settings(max_body_bytes=1024)))

        response = client.post("/api/chat", json={"message": "x" * 2000})

        assert response.status_code == 413
        assert response.json() == {"detail": TOO_LARGE_DETAIL}

    def test_rejects_a_streamed_body_that_grows_past_the_limit(self) -> None:
        client = TestClient(create_app(Settings(max_body_bytes=1024)))

        def chunks() -> Iterator[bytes]:
            yield b'{"message": "'
            for _ in range(10):
                yield b"x" * 512

        response = client.post(
            "/api/chat", content=chunks(), headers={"Content-Type": "application/json"}
        )

        assert response.status_code == 413
        assert response.json() == {"detail": TOO_LARGE_DETAIL}

    def test_accepts_a_body_within_the_limit(self) -> None:
        client = TestClient(create_app(Settings(max_body_bytes=1024)))
        assert client.post("/api/chat", json={"message": "hello"}).status_code == 200

    def test_a_non_numeric_content_length_is_left_to_the_server(self) -> None:
        client = TestClient(create_app(Settings(max_body_bytes=1024)))
        response = client.post(
            "/api/chat", json={"message": "hi"}, headers={"Content-Length": "abc"}
        )
        assert response.status_code != 413


class TestSecurityHeaders:
    def test_api_responses_carry_conservative_headers(self) -> None:
        response = TestClient(create_app()).get("/api/health")

        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert response.headers["Referrer-Policy"] == "no-referrer"
        assert response.headers["Cache-Control"] == "no-store"
        assert "default-src 'none'" in response.headers["Content-Security-Policy"]
        assert "frame-ancestors 'none'" in response.headers["Content-Security-Policy"]

    def test_error_responses_get_them_too(self) -> None:
        response = TestClient(create_app()).post("/api/chat", json={})
        assert response.status_code == 422
        assert response.headers["X-Content-Type-Options"] == "nosniff"

    def test_hsts_is_only_sent_in_production(self) -> None:
        assert (
            "Strict-Transport-Security" not in TestClient(create_app()).get("/api/health").headers
        )
        production = TestClient(create_app(PRODUCTION)).get("/api/health")
        assert "max-age=" in production.headers["Strict-Transport-Security"]

    def test_the_docs_page_is_not_given_the_api_csp(self) -> None:
        response = TestClient(create_app()).get("/docs")
        assert response.status_code == 200
        assert "Content-Security-Policy" not in response.headers
        assert response.headers["X-Content-Type-Options"] == "nosniff"


class TestProductionSurface:
    @pytest.mark.parametrize("path", ["/docs", "/redoc", "/openapi.json"])
    def test_interactive_docs_and_schema_are_off_in_production(self, path: str) -> None:
        assert TestClient(create_app(PRODUCTION)).get(path).status_code == 404

    @pytest.mark.parametrize("path", ["/docs", "/redoc", "/openapi.json"])
    def test_and_on_in_development(self, path: str) -> None:
        assert TestClient(create_app()).get(path).status_code == 200

    def test_the_api_itself_still_works_in_production(self) -> None:
        client = TestClient(create_app(PRODUCTION))
        assert client.get("/api/health").json() == {"status": "ok"}


class TestRequestId:
    def test_one_is_generated_when_the_client_sends_none(self) -> None:
        request_id = TestClient(create_app()).get("/api/health").headers["X-Request-ID"]
        assert re.fullmatch(r"[0-9a-f]{32}", request_id)

    def test_a_sensible_client_supplied_id_is_echoed(self) -> None:
        response = TestClient(create_app()).get("/api/health", headers={"X-Request-ID": "trace-42"})
        assert response.headers["X-Request-ID"] == "trace-42"

    def test_a_malformed_id_is_replaced(self) -> None:
        response = TestClient(create_app()).get(
            "/api/health", headers={"X-Request-ID": "bad id with spaces!"}
        )
        assert re.fullmatch(r"[0-9a-f]{32}", response.headers["X-Request-ID"])

    def test_an_overlong_id_is_replaced(self) -> None:
        response = TestClient(create_app()).get("/api/health", headers={"X-Request-ID": "a" * 65})
        assert re.fullmatch(r"[0-9a-f]{32}", response.headers["X-Request-ID"])


def access_records(caplog: pytest.LogCaptureFixture) -> list[logging.LogRecord]:
    return [r for r in caplog.records if r.name == "app.access"]


class TestAccessLog:
    def test_a_chat_request_logs_sizes_and_outcome_but_not_the_text(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        client = TestClient(create_app())
        with caplog.at_level(logging.INFO, logger="app.access"):
            client.post(
                "/api/chat",
                json={
                    "message": "my confidential question",
                    "history": [{"role": "user", "content": "earlier secret"}],
                },
            )

        (record,) = access_records(caplog)
        assert record.__dict__["method"] == "POST"
        assert record.__dict__["path"] == "/api/chat"
        assert record.__dict__["status"] == 200
        assert record.__dict__["engine"] == "stub"
        assert record.__dict__["message_chars"] == len("my confidential question")
        assert record.__dict__["history_turns"] == 1
        assert record.__dict__["duration_ms"] >= 0
        assert re.fullmatch(r"[0-9a-f]{32}", record.__dict__["request_id"])
        assert "confidential" not in caplog.text
        assert "secret" not in caplog.text

    def test_the_logged_id_matches_the_response_header(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        client = TestClient(create_app())
        with caplog.at_level(logging.INFO, logger="app.access"):
            response = client.post("/api/chat", json={"message": "hi"})

        (record,) = access_records(caplog)
        assert record.__dict__["request_id"] == response.headers["X-Request-ID"]

    @pytest.mark.parametrize(
        ("header", "expected"),
        [(None, 0), ("203.0.113.9", 1), ("203.0.113.9, 10.0.0.1 ,, 10.0.0.2", 3)],
    )
    def test_it_counts_forwarded_addresses_without_logging_them(
        self, caplog: pytest.LogCaptureFixture, header: str | None, expected: int
    ) -> None:
        client = TestClient(create_app())
        headers = {"X-Forwarded-For": header} if header else {}
        with caplog.at_level(logging.INFO, logger="app.access"):
            client.post("/api/chat", json={"message": "hi"}, headers=headers)

        (record,) = access_records(caplog)
        assert record.__dict__["forwarded_entries"] == expected
        assert "203.0.113.9" not in caplog.text

    def test_rate_limited_requests_are_marked(self, caplog: pytest.LogCaptureFixture) -> None:
        client = TestClient(create_app(Settings(rate_limit_per_minute=1)))
        client.post("/api/chat", json={"message": "hi"})
        caplog.clear()
        with caplog.at_level(logging.INFO, logger="app.access"):
            client.post("/api/chat", json={"message": "hi"})

        (record,) = access_records(caplog)
        assert record.__dict__["status"] == 429
        assert record.__dict__["rate_limited"] is True

    def test_health_checks_are_quiet_unless_debugging(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        client = TestClient(create_app())
        with caplog.at_level(logging.INFO, logger="app.access"):
            client.get("/api/health")
        assert access_records(caplog) == []

        with caplog.at_level(logging.DEBUG, logger="app.access"):
            client.get("/api/health")
        assert len(access_records(caplog)) == 1

    def test_an_unhandled_error_is_logged_as_a_500(self, caplog: pytest.LogCaptureFixture) -> None:
        app = create_app()

        @app.get("/boom")
        def boom() -> None:
            raise RuntimeError("kaboom")

        client = TestClient(app, raise_server_exceptions=False)
        with caplog.at_level(logging.INFO, logger="app.access"):
            response = client.get("/boom")

        assert response.status_code == 500
        (record,) = access_records(caplog)
        assert record.__dict__["status"] == 500
