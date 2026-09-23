"""Talking to the language model provider.

The engine depends on the small `Completer` interface, not on an SDK, so tests use a fake and the
provider can change without touching the engine. `AnthropicCompleter` is the real one.
"""

from dataclasses import dataclass
from typing import Literal, Protocol

import anthropic
import httpx2
from anthropic.types import MessageParam
from pydantic import SecretStr


class ProviderError(Exception):
    """The provider could not answer: timeout, rate limit, outage, rejected key or empty reply.

    Carries only a kind and an HTTP status, never provider text, so it is safe to log.
    """

    def __init__(self, kind: str, status: int | None = None) -> None:
        super().__init__(f"{kind} ({status})" if status else kind)
        self.kind = kind
        self.status = status


@dataclass(frozen=True)
class Turn:
    role: Literal["user", "assistant"]
    content: str


@dataclass(frozen=True)
class Completion:
    text: str
    input_tokens: int
    output_tokens: int


class Completer(Protocol):
    async def complete(self, *, system: str, turns: list[Turn], max_tokens: int) -> Completion: ...


class AnthropicCompleter:
    def __init__(
        self,
        *,
        api_key: SecretStr,
        model: str,
        timeout_seconds: float,
        max_retries: int = 1,
        http_client: httpx2.AsyncClient | None = None,
    ) -> None:
        self._model = model
        # The SDK retries connection errors, 429s and 5xx once, with backoff, before giving up.
        self._client = anthropic.AsyncAnthropic(
            api_key=api_key.get_secret_value(),
            timeout=timeout_seconds,
            max_retries=max_retries,
            http_client=http_client,
        )

    async def complete(self, *, system: str, turns: list[Turn], max_tokens: int) -> Completion:
        messages = [MessageParam(role=turn.role, content=turn.content) for turn in turns]
        try:
            response = await self._client.messages.create(
                model=self._model, max_tokens=max_tokens, system=system, messages=messages
            )
        except anthropic.APIStatusError as error:
            raise ProviderError("status", error.status_code) from error
        except anthropic.APIError as error:  # timeouts and connection failures
            raise ProviderError(type(error).__name__) from error

        text = "".join(block.text for block in response.content if block.type == "text").strip()
        if not text:
            raise ProviderError("empty")
        return Completion(
            text=text,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
        )
