import asyncio
import json
from collections.abc import Callable

import httpx2
import pytest
from pydantic import SecretStr

from app.services.completion import AnthropicCompleter, Completion, ProviderError, Turn

Handler = Callable[[httpx2.Request], httpx2.Response]


def message_response(text: str = "Hello there.") -> httpx2.Response:
    return httpx2.Response(
        200,
        json={
            "id": "msg_1",
            "type": "message",
            "role": "assistant",
            "model": "claude-haiku-4-5-20251001",
            "content": [{"type": "text", "text": text}],
            "stop_reason": "end_turn",
            "stop_sequence": None,
            "usage": {"input_tokens": 120, "output_tokens": 15},
        },
    )


def completer(handler: Handler) -> AnthropicCompleter:
    return AnthropicCompleter(
        api_key=SecretStr("sk-test"),
        model="claude-haiku-4-5-20251001",
        timeout_seconds=5,
        max_retries=0,
        http_client=httpx2.AsyncClient(transport=httpx2.MockTransport(handler)),
    )


def complete(engine: AnthropicCompleter) -> Completion:
    return asyncio.run(
        engine.complete(system="be brief", turns=[Turn("user", "hi")], max_tokens=50)
    )


def test_sends_the_prompt_and_reads_text_and_token_counts() -> None:
    seen: list[dict[str, object]] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        seen.append(json.loads(request.content))
        assert request.headers["x-api-key"] == "sk-test"
        return message_response("  Hello there.  ")

    result = complete(completer(handler))

    assert result == Completion(text="Hello there.", input_tokens=120, output_tokens=15)
    assert seen[0]["model"] == "claude-haiku-4-5-20251001"
    assert seen[0]["max_tokens"] == 50
    assert seen[0]["system"] == "be brief"
    assert seen[0]["messages"] == [{"role": "user", "content": "hi"}]


@pytest.mark.parametrize("status", [400, 401, 429, 500, 529])
def test_an_http_error_becomes_a_provider_error_with_its_status(status: int) -> None:
    def handler(request: httpx2.Request) -> httpx2.Response:
        body = {"type": "error", "error": {"type": "x", "message": "SECRET DETAIL"}}
        return httpx2.Response(status, json=body)

    with pytest.raises(ProviderError) as caught:
        complete(completer(handler))

    assert (caught.value.kind, caught.value.status) == ("status", status)
    assert "SECRET DETAIL" not in str(caught.value)


def test_a_dropped_connection_becomes_a_provider_error() -> None:
    def handler(request: httpx2.Request) -> httpx2.Response:
        raise httpx2.ConnectError("no route", request=request)

    with pytest.raises(ProviderError) as caught:
        complete(completer(handler))

    assert caught.value.kind == "APIConnectionError"
    assert caught.value.status is None


def test_an_empty_reply_is_a_provider_error() -> None:
    with pytest.raises(ProviderError, match="empty"):
        complete(completer(lambda request: message_response("   ")))
