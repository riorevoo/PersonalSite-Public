"""Answer generation.

An engine is anything that satisfies the `Answerer` protocol. Register it in `ENGINES` and add its
name to `Settings.answerer`; `get_answerer` then selects it from `APP_ANSWERER`. Two exist: the
placeholder `stub` and the hosted-LLM engine in `app/services/llm.py`. Routes depend only on the
protocol, never on a concrete engine.
"""

import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, Protocol, cast

from fastapi import Request

from app.core.config import Settings
from app.schemas.chat import ChatTurn
from app.services.errors import EngineUnavailableError
from app.services.knowledge import KnowledgeBase

if TYPE_CHECKING:
    from app.services.runtime import AppServices

__all__ = [
    "CANNED",
    "ENGINES",
    "FALLBACK",
    "Answerer",
    "EngineUnavailableError",
    "StubAnswerer",
    "build_answerer",
    "get_answerer",
]

logger = logging.getLogger(__name__)

FALLBACK = (
    "I only have answers for a handful of things right now, and I'd rather say so than make "
    "something up. Try one of the suggestions, or email him and he'll answer it himself."
)

# Placeholder copy for the stub engine, used when no LLM key is configured.
CANNED: dict[str, str] = {
    "what experience do you have?": "Placeholder: his experience will be summarised here.",
    "what projects have you worked on?": "Placeholder: his projects will be summarised here.",
    "what are you interested in right now?": "Placeholder: what he's into right now goes here.",
}


class Answerer(Protocol):
    async def answer(self, message: str, history: list[ChatTurn]) -> str:
        """Answer one question, or raise `EngineUnavailableError` when it cannot."""
        ...


class StubAnswerer:
    """Exact-match lookup on the suggestion chips, with an honest fallback."""

    async def answer(self, message: str, history: list[ChatTurn]) -> str:
        return CANNED.get(message.strip().lower(), FALLBACK)


def _build_llm(settings: Settings, knowledge: KnowledgeBase) -> Answerer:
    if settings.llm_api_key is None:
        logger.warning("APP_ANSWERER=llm but APP_LLM_API_KEY is not set: using the stub engine.")
        return StubAnswerer()
    from app.services.llm import build_llm_answerer  # imported late: it needs the SDK and Firestore

    return build_llm_answerer(settings, knowledge)


ENGINES: dict[str, Callable[[Settings, KnowledgeBase], Answerer]] = {
    "stub": lambda _settings, _knowledge: StubAnswerer(),
    "llm": _build_llm,
}


def build_answerer(settings: Settings, knowledge: KnowledgeBase) -> Answerer:
    return ENGINES[settings.answerer](settings, knowledge)


def get_answerer(request: Request) -> Answerer:
    services = cast("AppServices", request.app.state.services)
    return services.answerer
