from collections.abc import Iterator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.main import create_app
from app.schemas.chat import ChatTurn
from app.services.answerer import get_answerer


class RecordingAnswerer:
    """Fake engine that records what it was asked and returns a fixed answer."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, list[ChatTurn]]] = []

    async def answer(self, message: str, history: list[ChatTurn]) -> str:
        self.calls.append((message, history))
        return "fake answer"


@pytest.fixture
def app() -> FastAPI:
    return create_app()


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app) as client:
        yield client


@pytest.fixture
def answerer_override(app: FastAPI) -> Iterator[RecordingAnswerer]:
    """Swap the engine behind /api/chat for a recording fake; restored after the test."""
    fake = RecordingAnswerer()
    app.dependency_overrides[get_answerer] = lambda: fake
    yield fake
    app.dependency_overrides.pop(get_answerer, None)
