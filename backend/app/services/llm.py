"""The hosted-LLM answering engine, with its spend ceilings.

Order of business for each question: the spend counters are checked, and at a ceiling the visitor
gets the cap message instead of a model call; otherwise the model answers from the knowledge base
(faq.md included, as guidance) and the cost is recorded. A question that matches an faq.md heading
is the exception: when the model cannot answer (a ceiling, an outage, or spend that cannot be
checked) the visitor gets that hand-written answer instead of the cap message or an error. With no
matching entry, a provider failure or unknown spend is reported (503) rather than guessed at. Logs
carry sizes, sources and costs, never visitor text.
"""

import logging
import math
from collections.abc import Callable
from datetime import UTC, datetime

from app.core.config import Settings
from app.schemas.chat import ChatTurn
from app.services.completion import AnthropicCompleter, Completer, Completion, ProviderError
from app.services.errors import EngineUnavailableError
from app.services.knowledge import KnowledgeBase
from app.services.prompt import PromptBuilder
from app.services.usage import Spend, UsageStore, build_usage_store

logger = logging.getLogger(__name__)

MICRO = 1_000_000
# Share of a ceiling at which a `budget_threshold` warning is logged (feeds the email alert).
THRESHOLD_PERCENTS = (50, 80, 100)


def month_cap_message(owner: str) -> str:
    return (
        f"Someone asked me too many questions this month; {owner} doesn't pay enough for me "
        "to answer more. Sorry!"
    )


def day_cap_message(owner: str) -> str:
    return (
        f"Someone asked me too many questions today; {owner} doesn't pay enough for me to "
        "answer more today. Try again tomorrow. Sorry!"
    )


class LlmAnswerer:
    def __init__(
        self,
        *,
        settings: Settings,
        knowledge: KnowledgeBase,
        completer: Completer,
        store: UsageStore,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._settings = settings
        self._knowledge = knowledge
        self._completer = completer
        self._store = store
        self._clock = clock
        self._prompt = PromptBuilder(
            owner=settings.owner_name, knowledge=knowledge, history_turns=settings.llm_history_turns
        )
        self._month_cap = round(settings.monthly_budget_usd * MICRO)
        self._day_cap = round(settings.daily_budget_usd * MICRO)

    async def answer(self, message: str, history: list[ChatTurn]) -> str:
        message = message.strip()
        faq = self._knowledge.faq_answer(message)
        now = self._clock()
        try:
            spend = await self._spend(now)
            scope = self._ceiling_reached(spend)
            if scope is None:
                return await self._ask_model(message, history, now, spend)
        except EngineUnavailableError:
            if faq is None:
                raise
            return self._faq_fallback(faq, reason="unavailable")

        logger.warning("chat capped", extra={"event": "chat_capped", "scope": scope})
        if faq is not None:
            return self._faq_fallback(faq, reason=f"capped_{scope}")
        owner = self._settings.owner_name
        return month_cap_message(owner) if scope == "month" else day_cap_message(owner)

    def _ceiling_reached(self, spend: Spend) -> str | None:
        if spend.month_micro_usd >= self._month_cap:
            return "month"
        if spend.day_micro_usd >= self._day_cap:
            return "day"
        return None

    def _faq_fallback(self, faq: str, *, reason: str) -> str:
        logger.info(
            "chat answered",
            extra={"event": "chat_answer", "source": "faq_fallback", "reason": reason},
        )
        return faq

    async def _ask_model(
        self, message: str, history: list[ChatTurn], now: datetime, spend: Spend
    ) -> str:
        try:
            completion = await self._completer.complete(
                system=self._prompt.system(now.date()),
                turns=self._prompt.turns(history, message),
                max_tokens=self._settings.llm_max_tokens,
            )
        except ProviderError as error:
            logger.error(
                "provider error",
                extra={"event": "provider_error", "kind": error.kind, "status": error.status},
            )
            raise EngineUnavailableError from error

        await self._record(now, spend, completion)
        return completion.text

    async def _spend(self, now: datetime) -> Spend:
        try:
            return await self._store.spend(now)
        except Exception as error:
            # Without the counters the ceilings cannot be enforced, so do not spend.
            logger.error(
                "usage store unavailable",
                extra={"event": "usage_unavailable", "error": type(error).__name__},
            )
            raise EngineUnavailableError from error

    def _cost_micro_usd(self, completion: Completion) -> int:
        settings = self._settings
        # A price per million tokens is the same number as micro-dollars per token.
        return math.ceil(
            completion.input_tokens * settings.llm_input_usd_per_mtok
            + completion.output_tokens * settings.llm_output_usd_per_mtok
        )

    async def _record(self, now: datetime, before: Spend, completion: Completion) -> None:
        cost = self._cost_micro_usd(completion)
        logger.info(
            "chat answered",
            extra={
                "event": "chat_answer",
                "source": "llm",
                "input_tokens": completion.input_tokens,
                "output_tokens": completion.output_tokens,
                "cost_usd": cost / MICRO,
            },
        )
        try:
            await self._store.record(
                now,
                micro_usd=cost,
                input_tokens=completion.input_tokens,
                output_tokens=completion.output_tokens,
            )
        except Exception as error:
            logger.error(
                "usage not recorded",
                extra={"event": "usage_record_failed", "error": type(error).__name__},
            )
            return
        self._warn_on_thresholds("month", before.month_micro_usd, cost, self._month_cap)
        self._warn_on_thresholds("day", before.day_micro_usd, cost, self._day_cap)

    @staticmethod
    def _warn_on_thresholds(scope: str, before: int, cost: int, cap: int) -> None:
        for percent in THRESHOLD_PERCENTS:
            line = cap * percent / 100
            if before < line <= before + cost:
                logger.warning(
                    "budget threshold crossed",
                    extra={
                        "event": "budget_threshold",
                        "scope": scope,
                        "percent": percent,
                        "spent_usd": (before + cost) / MICRO,
                        "budget_usd": cap / MICRO,
                    },
                )


def build_llm_answerer(settings: Settings, knowledge: KnowledgeBase) -> LlmAnswerer:
    """The production wiring: the real provider and the configured spend store."""
    if settings.llm_api_key is None:
        raise ValueError("APP_LLM_API_KEY is required for the llm engine.")
    return LlmAnswerer(
        settings=settings,
        knowledge=knowledge,
        completer=AnthropicCompleter(
            api_key=settings.llm_api_key,
            model=settings.llm_model,
            timeout_seconds=settings.llm_timeout_seconds,
        ),
        store=build_usage_store(settings),
    )
