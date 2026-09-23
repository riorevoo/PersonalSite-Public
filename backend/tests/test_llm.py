import asyncio
import logging
from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.core.config import Settings
from app.schemas.chat import ChatTurn
from app.services.completion import Completion, ProviderError, Turn
from app.services.errors import EngineUnavailableError
from app.services.knowledge import KnowledgeBase, load_knowledge
from app.services.llm import LlmAnswerer, build_llm_answerer, day_cap_message, month_cap_message
from app.services.usage import InMemoryUsageStore, Spend
from tests.helpers import write_post

NOW = datetime(2026, 9, 21, 12, 0, tzinfo=UTC)
FAQ_QUESTION = "what experience do you have?"
FAQ_ANSWER = "Five years of backend work."
# Costs 1000 * $1 + 100 * $5 per million tokens = 1500 micro-dollars.
COMPLETION = Completion(text="He builds APIs.", input_tokens=1000, output_tokens=100)
COST = 1500


class FakeCompleter:
    def __init__(self, error: ProviderError | None = None) -> None:
        self.error = error
        self.calls: list[tuple[str, list[Turn], int]] = []

    async def complete(self, *, system: str, turns: list[Turn], max_tokens: int) -> Completion:
        self.calls.append((system, turns, max_tokens))
        if self.error:
            raise self.error
        return COMPLETION


class BrokenStore(InMemoryUsageStore):
    def __init__(self, *, fail_reads: bool = False, fail_writes: bool = False) -> None:
        super().__init__()
        self.fail_reads = fail_reads
        self.fail_writes = fail_writes

    async def spend(self, now: datetime) -> Spend:
        if self.fail_reads:
            raise ConnectionError("firestore is down")
        return await super().spend(now)

    async def record(
        self, now: datetime, *, micro_usd: int, input_tokens: int, output_tokens: int
    ) -> None:
        if self.fail_writes:
            raise ConnectionError("firestore is down")
        await super().record(
            now, micro_usd=micro_usd, input_tokens=input_tokens, output_tokens=output_tokens
        )


@pytest.fixture
def knowledge(tmp_path: Path) -> KnowledgeBase:
    (tmp_path / "profile.md").write_text(
        "---\ntitle: Profile\n---\n\n## Bio\nHe lives on the moon.\n", encoding="utf-8"
    )
    (tmp_path / "boundaries.md").write_text(
        "---\ntitle: Boundaries\n---\n\n## Never discuss\nSalary.\n", encoding="utf-8"
    )
    (tmp_path / "faq.md").write_text(
        f"---\ntitle: FAQ\n---\n\n## {FAQ_QUESTION}\n{FAQ_ANSWER}\n", encoding="utf-8"
    )
    write_post(tmp_path, "2026-08-14-secret-post", body="POST-ONLY-TEXT here.\n")
    return load_knowledge(tmp_path)


def make(
    knowledge: KnowledgeBase,
    *,
    completer: FakeCompleter | None = None,
    store: InMemoryUsageStore | None = None,
    **settings: object,
) -> LlmAnswerer:
    budgets = {"monthly_budget_usd": 0.01, "daily_budget_usd": 0.005, **settings}
    return LlmAnswerer(
        settings=Settings(**budgets),  # type: ignore[arg-type]
        knowledge=knowledge,
        completer=completer or FakeCompleter(),
        store=store or InMemoryUsageStore(),
        clock=lambda: NOW,
    )


def ask(
    engine: LlmAnswerer, message: str = "what does he build?", history: list[ChatTurn] | None = None
) -> str:
    return asyncio.run(engine.answer(message, history or []))


def events(caplog: pytest.LogCaptureFixture, name: str) -> list[logging.LogRecord]:
    return [r for r in caplog.records if getattr(r, "event", None) == name]


class TestAnswering:
    def test_a_faq_question_still_goes_to_the_model_with_the_faq_as_guidance(
        self, knowledge: KnowledgeBase
    ) -> None:
        completer, store = FakeCompleter(), InMemoryUsageStore()
        engine = make(knowledge, completer=completer, store=store)

        assert ask(engine, f"  {FAQ_QUESTION.upper()} ") == COMPLETION.text
        assert len(completer.calls) == 1
        assert FAQ_ANSWER in completer.calls[0][0]
        assert asyncio.run(store.spend(NOW)) == Spend(month_micro_usd=COST, day_micro_usd=COST)

    def test_the_model_answers_and_the_cost_is_recorded(self, knowledge: KnowledgeBase) -> None:
        store = InMemoryUsageStore()
        engine = make(knowledge, store=store)

        assert ask(engine) == "He builds APIs."
        assert asyncio.run(store.spend(NOW)) == Spend(month_micro_usd=COST, day_micro_usd=COST)

    def test_the_call_uses_the_configured_limits(self, knowledge: KnowledgeBase) -> None:
        completer = FakeCompleter()
        ask(make(knowledge, completer=completer, llm_max_tokens=123))

        _, _, max_tokens = completer.calls[0]
        assert max_tokens == 123

    def test_the_prompt_carries_the_persona_boundaries_and_knowledge_but_no_posts(
        self, knowledge: KnowledgeBase
    ) -> None:
        completer = FakeCompleter()
        ask(make(knowledge, completer=completer, owner_name="Ada"))

        system = completer.calls[0][0]
        assert "AI answering service on Ada's personal website" in system
        assert "2026-09-21" in system
        assert "He lives on the moon." in system
        assert "<boundaries>" in system
        assert "Salary." in system
        assert "POST-ONLY-TEXT" not in system

    def test_recent_history_is_sent_with_the_question(self, knowledge: KnowledgeBase) -> None:
        completer = FakeCompleter()
        history = [
            ChatTurn(role="user", content="hi"),
            ChatTurn(role="assistant", content="hello"),
        ]
        ask(make(knowledge, completer=completer), "and now?", history)

        assert completer.calls[0][1] == [
            Turn("user", "hi"),
            Turn("assistant", "hello"),
            Turn("user", "and now?"),
        ]


class TestCeilings:
    def test_at_the_monthly_ceiling_the_visitor_gets_the_cap_message_and_no_model_call(
        self, knowledge: KnowledgeBase, caplog: pytest.LogCaptureFixture
    ) -> None:
        completer, store = FakeCompleter(), InMemoryUsageStore()
        asyncio.run(store.record(NOW, micro_usd=10_000, input_tokens=0, output_tokens=0))

        with caplog.at_level(logging.INFO):
            answer = ask(make(knowledge, completer=completer, store=store))

        assert answer == month_cap_message("Site Owner")
        assert answer == (
            "Someone asked me too many questions this month; Site Owner doesn't pay enough for me "
            "to answer more. Sorry!"
        )
        assert completer.calls == []
        assert events(caplog, "chat_capped")[0].scope == "month"  # type: ignore[attr-defined]

    def test_at_the_daily_ceiling_the_message_says_today(self, knowledge: KnowledgeBase) -> None:
        store = InMemoryUsageStore()
        # $0.005 a day is reached while the month ($0.01) still has room.
        asyncio.run(store.record(NOW, micro_usd=5_000, input_tokens=0, output_tokens=0))

        assert ask(make(knowledge, store=store)) == day_cap_message("Site Owner")
        assert "today" in day_cap_message("Site Owner")

    def test_a_faq_question_gets_its_written_answer_at_the_monthly_ceiling(
        self, knowledge: KnowledgeBase, caplog: pytest.LogCaptureFixture
    ) -> None:
        completer, store = FakeCompleter(), InMemoryUsageStore()
        asyncio.run(store.record(NOW, micro_usd=10_000, input_tokens=0, output_tokens=0))

        with caplog.at_level(logging.INFO):
            answer = ask(make(knowledge, completer=completer, store=store), FAQ_QUESTION)

        assert answer == FAQ_ANSWER
        assert completer.calls == []
        answered = events(caplog, "chat_answer")[0]
        assert (answered.source, answered.reason) == ("faq_fallback", "capped_month")  # type: ignore[attr-defined]
        assert events(caplog, "chat_capped")[0].scope == "month"  # type: ignore[attr-defined]

    def test_a_faq_question_gets_its_written_answer_at_the_daily_ceiling(
        self, knowledge: KnowledgeBase, caplog: pytest.LogCaptureFixture
    ) -> None:
        store = InMemoryUsageStore()
        asyncio.run(store.record(NOW, micro_usd=5_000, input_tokens=0, output_tokens=0))

        with caplog.at_level(logging.INFO):
            assert ask(make(knowledge, store=store), FAQ_QUESTION) == FAQ_ANSWER

        assert events(caplog, "chat_answer")[0].reason == "capped_day"  # type: ignore[attr-defined]

    def test_a_placeholder_faq_entry_is_not_shown_at_the_ceiling(self, tmp_path: Path) -> None:
        (tmp_path / "faq.md").write_text(
            f"---\ntitle: FAQ\n---\n\n## {FAQ_QUESTION}\nTODO(owner): write the answer.\n",
            encoding="utf-8",
        )
        store = InMemoryUsageStore()
        asyncio.run(store.record(NOW, micro_usd=10_000, input_tokens=0, output_tokens=0))

        answer = ask(make(load_knowledge(tmp_path), store=store), FAQ_QUESTION)

        assert answer == month_cap_message("Site Owner")

    def test_the_owner_name_comes_from_settings(self, knowledge: KnowledgeBase) -> None:
        store = InMemoryUsageStore()
        asyncio.run(store.record(NOW, micro_usd=10_000, input_tokens=0, output_tokens=0))

        assert "Ada doesn't pay enough" in ask(make(knowledge, store=store, owner_name="Ada"))

    def test_spend_from_earlier_days_does_not_block_today(self, knowledge: KnowledgeBase) -> None:
        store = InMemoryUsageStore()
        yesterday = datetime(2026, 9, 20, 12, 0, tzinfo=UTC)
        asyncio.run(store.record(yesterday, micro_usd=5_000, input_tokens=0, output_tokens=0))

        assert ask(make(knowledge, store=store)) == "He builds APIs."


class TestThresholds:
    def test_crossing_each_share_of_the_ceiling_logs_one_warning(
        self, knowledge: KnowledgeBase, caplog: pytest.LogCaptureFixture
    ) -> None:
        # Day and month share a 10000 micro-dollar ceiling; each question costs 1500.
        engine = make(knowledge, daily_budget_usd=0.01)
        with caplog.at_level(logging.INFO):
            for _ in range(7):
                ask(engine)

        crossed = [
            (r.scope, r.percent)  # type: ignore[attr-defined]
            for r in events(caplog, "budget_threshold")
        ]
        # 50% is crossed by question 4 (4500 to 6000), 80% by 6 (7500 to 9000), 100% by 7.
        assert crossed == [
            ("month", 50),
            ("day", 50),
            ("month", 80),
            ("day", 80),
            ("month", 100),
            ("day", 100),
        ]
        assert all(r.levelno == logging.WARNING for r in events(caplog, "budget_threshold"))

    def test_a_ceiling_crossed_by_one_answer_blocks_the_next_question(
        self, knowledge: KnowledgeBase
    ) -> None:
        engine = make(knowledge, daily_budget_usd=0.01)
        answers = [ask(engine) for _ in range(8)]

        assert answers[:7] == ["He builds APIs."] * 7
        assert answers[7] == month_cap_message("Site Owner")

    def test_every_answer_logs_tokens_and_cost_but_no_text(
        self, knowledge: KnowledgeBase, caplog: pytest.LogCaptureFixture
    ) -> None:
        with caplog.at_level(logging.INFO):
            ask(make(knowledge), "my secret question")

        record = events(caplog, "chat_answer")[0]
        assert (record.input_tokens, record.output_tokens) == (1000, 100)  # type: ignore[attr-defined]
        assert record.cost_usd == COST / 1_000_000  # type: ignore[attr-defined]
        assert "secret" not in caplog.text


class TestFailures:
    def test_a_provider_failure_becomes_engine_unavailable_and_costs_nothing(
        self, knowledge: KnowledgeBase, caplog: pytest.LogCaptureFixture
    ) -> None:
        store = InMemoryUsageStore()
        engine = make(knowledge, completer=FakeCompleter(ProviderError("status", 529)), store=store)

        with caplog.at_level(logging.INFO), pytest.raises(EngineUnavailableError):
            ask(engine)

        assert asyncio.run(store.spend(NOW)) == Spend()
        failure = events(caplog, "provider_error")[0]
        assert (failure.kind, failure.status) == ("status", 529)  # type: ignore[attr-defined]

    def test_a_provider_failure_gives_a_faq_question_its_written_answer(
        self, knowledge: KnowledgeBase, caplog: pytest.LogCaptureFixture
    ) -> None:
        store = InMemoryUsageStore()
        engine = make(knowledge, completer=FakeCompleter(ProviderError("status", 529)), store=store)

        with caplog.at_level(logging.INFO):
            assert ask(engine, FAQ_QUESTION) == FAQ_ANSWER

        assert asyncio.run(store.spend(NOW)) == Spend()
        assert events(caplog, "chat_answer")[0].reason == "unavailable"  # type: ignore[attr-defined]

    def test_unknown_spend_gives_a_faq_question_its_written_answer_without_the_model(
        self, knowledge: KnowledgeBase
    ) -> None:
        completer = FakeCompleter()
        engine = make(knowledge, completer=completer, store=BrokenStore(fail_reads=True))

        assert ask(engine, FAQ_QUESTION) == FAQ_ANSWER
        assert completer.calls == []

    def test_unknown_spend_fails_closed_without_calling_the_model(
        self, knowledge: KnowledgeBase
    ) -> None:
        completer = FakeCompleter()
        engine = make(knowledge, completer=completer, store=BrokenStore(fail_reads=True))

        with pytest.raises(EngineUnavailableError):
            ask(engine)
        assert completer.calls == []

    def test_a_failed_write_still_delivers_the_answer_and_logs_an_error(
        self, knowledge: KnowledgeBase, caplog: pytest.LogCaptureFixture
    ) -> None:
        engine = make(knowledge, store=BrokenStore(fail_writes=True))

        with caplog.at_level(logging.INFO):
            assert ask(engine) == "He builds APIs."

        assert events(caplog, "usage_record_failed")[0].levelno == logging.ERROR
        assert events(caplog, "budget_threshold") == []


class TestWiring:
    def test_building_without_a_key_is_refused(self, knowledge: KnowledgeBase) -> None:
        with pytest.raises(ValueError, match="APP_LLM_API_KEY"):
            build_llm_answerer(Settings(), knowledge)

    def test_building_with_a_key_uses_the_real_provider_and_an_in_memory_store(
        self, knowledge: KnowledgeBase
    ) -> None:
        engine = build_llm_answerer(Settings(llm_api_key="sk-test"), knowledge)  # type: ignore[arg-type]

        assert isinstance(engine, LlmAnswerer)
