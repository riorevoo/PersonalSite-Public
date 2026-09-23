"""Spend counting for the LLM engine.

Cost is kept as integer micro-dollars (one million per dollar), so counting never drifts. Months
and days are UTC calendar periods, like the provider's billing. Firestore is used in production
because Cloud Run wipes local state whenever an instance stops; memory is for development and tests.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from google.cloud.firestore import AsyncClient, AsyncDocumentReference, Increment

from app.core.config import Settings


@dataclass(frozen=True)
class Spend:
    month_micro_usd: int = 0
    day_micro_usd: int = 0


class UsageStore(Protocol):
    async def spend(self, now: datetime) -> Spend: ...

    async def record(
        self, now: datetime, *, micro_usd: int, input_tokens: int, output_tokens: int
    ) -> None: ...


def month_key(now: datetime) -> str:
    return f"month-{now:%Y-%m}"


def day_key(now: datetime) -> str:
    return f"day-{now:%Y-%m-%d}"


class InMemoryUsageStore:
    """Counts in this process only: it resets on restart, so never use it in production."""

    def __init__(self) -> None:
        self._micro_usd: dict[str, int] = {}

    async def spend(self, now: datetime) -> Spend:
        return Spend(
            month_micro_usd=self._micro_usd.get(month_key(now), 0),
            day_micro_usd=self._micro_usd.get(day_key(now), 0),
        )

    async def record(
        self, now: datetime, *, micro_usd: int, input_tokens: int, output_tokens: int
    ) -> None:
        for key in (month_key(now), day_key(now)):
            self._micro_usd[key] = self._micro_usd.get(key, 0) + micro_usd


class FirestoreUsageStore:
    """One document per month and per day, updated with atomic increments.

    Each document also keeps token and question counts, so `scripts/usage_report.py` and the
    Firebase console can show usage without any visitor text ever being stored.
    """

    def __init__(self, collection: str, client: AsyncClient | None = None) -> None:
        self._collection = collection
        self._client = client or AsyncClient()

    def _document(self, key: str) -> AsyncDocumentReference:
        return self._client.collection(self._collection).document(key)

    async def spend(self, now: datetime) -> Spend:
        refs = [self._document(month_key(now)), self._document(day_key(now))]
        found: dict[str, int] = {}
        async for snapshot in self._client.get_all(refs):
            if snapshot.exists:
                found[snapshot.id] = int(snapshot.get("micro_usd") or 0)
        return Spend(
            month_micro_usd=found.get(month_key(now), 0),
            day_micro_usd=found.get(day_key(now), 0),
        )

    async def record(
        self, now: datetime, *, micro_usd: int, input_tokens: int, output_tokens: int
    ) -> None:
        batch = self._client.batch()
        for key in (month_key(now), day_key(now)):
            batch.set(
                self._document(key),
                {
                    "micro_usd": Increment(micro_usd),
                    "input_tokens": Increment(input_tokens),
                    "output_tokens": Increment(output_tokens),
                    "questions": Increment(1),
                },
                merge=True,
            )
        await batch.commit()


def build_usage_store(settings: Settings) -> UsageStore:
    if settings.usage_store == "firestore":
        return FirestoreUsageStore(settings.usage_collection)
    return InMemoryUsageStore()
