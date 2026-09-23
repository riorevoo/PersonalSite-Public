import asyncio
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.config import Settings
from app.main import create_app
from app.services.answerer import CANNED, ENGINES, FALLBACK, StubAnswerer
from app.services.knowledge import KnowledgeBase
from app.services.llm import LlmAnswerer
from app.services.runtime import AppServices


def test_stub_is_the_default_engine() -> None:
    assert Settings().answerer == "stub"
    assert isinstance(AppServices(Settings()).answerer, StubAnswerer)


def test_engines_are_built_once() -> None:
    services = AppServices(Settings())
    assert services.answerer is services.answerer


def test_apps_build_separate_engines_with_their_own_settings(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen: list[Settings] = []

    def build(settings: Settings, knowledge: KnowledgeBase) -> StubAnswerer:
        seen.append(settings)
        return StubAnswerer()

    monkeypatch.setitem(ENGINES, "stub", build)
    first = Settings(knowledge_dir=tmp_path, max_message_chars=100)
    second = Settings(knowledge_dir=tmp_path, max_message_chars=200)
    with TestClient(create_app(first)) as one, TestClient(create_app(second)) as two:
        for client in (one, two):
            assert client.post("/api/chat", json={"message": "hi"}).status_code == 200
            assert client.post("/api/chat", json={"message": "again"}).status_code == 200
    assert seen == [first, second]


def test_unknown_engine_is_rejected_at_startup() -> None:
    with pytest.raises(ValidationError):
        Settings(answerer="does-not-exist")  # type: ignore[arg-type]


def test_stub_matches_chips_case_insensitively_and_falls_back() -> None:
    stub = StubAnswerer()
    question = next(iter(CANNED))

    assert asyncio.run(stub.answer(f"  {question.upper()}  ", [])) == CANNED[question]
    assert asyncio.run(stub.answer("something else entirely", [])) == FALLBACK


class TestLlmEngine:
    def test_without_a_key_it_falls_back_to_the_stub_and_says_so(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        with caplog.at_level("WARNING"):
            engine = AppServices(Settings(answerer="llm")).answerer

        assert isinstance(engine, StubAnswerer)
        assert "APP_LLM_API_KEY is not set" in caplog.text

    def test_with_a_key_the_hosted_engine_is_built(self) -> None:
        settings = Settings(answerer="llm", llm_api_key="sk-test")  # type: ignore[arg-type]

        assert isinstance(AppServices(settings).answerer, LlmAnswerer)

    def test_the_stub_words_its_replies_about_the_owner_in_the_third_person(self) -> None:
        assert "him" in FALLBACK
        assert all(" my " not in f" {text} " for text in CANNED.values())
