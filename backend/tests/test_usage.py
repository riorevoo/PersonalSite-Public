import asyncio
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import cast

import pytest
from google.cloud.firestore import AsyncClient

import app.services.usage as usage
from app.core.config import Settings
from app.services.usage import (
    FirestoreUsageStore,
    InMemoryUsageStore,
    Spend,
    build_usage_store,
    day_key,
    month_key,
)

NOW = datetime(2026, 9, 21, 23, 59, tzinfo=UTC)
NEXT_DAY = datetime(2026, 9, 22, 0, 1, tzinfo=UTC)
NEXT_MONTH = datetime(2026, 10, 1, 0, 1, tzinfo=UTC)


def test_keys_are_utc_calendar_periods() -> None:
    assert (month_key(NOW), day_key(NOW)) == ("month-2026-09", "day-2026-09-21")


class TestInMemory:
    def test_starts_at_zero(self) -> None:
        assert asyncio.run(InMemoryUsageStore().spend(NOW)) == Spend()

    def test_adds_up_by_day_and_month(self) -> None:
        store = InMemoryUsageStore()

        async def run() -> tuple[Spend, Spend, Spend]:
            await store.record(NOW, micro_usd=100, input_tokens=1, output_tokens=1)
            await store.record(NOW, micro_usd=50, input_tokens=1, output_tokens=1)
            return (
                await store.spend(NOW),
                await store.spend(NEXT_DAY),
                await store.spend(NEXT_MONTH),
            )

        today, tomorrow, next_month = asyncio.run(run())

        assert today == Spend(month_micro_usd=150, day_micro_usd=150)
        assert tomorrow == Spend(month_micro_usd=150, day_micro_usd=0)
        assert next_month == Spend()


class FakeSnapshot:
    def __init__(self, key: str, data: dict[str, int] | None) -> None:
        self.id = key
        self.exists = data is not None
        self._data = data or {}

    def get(self, field: str) -> int | None:
        return self._data.get(field)


class FakeReference:
    def __init__(self, key: str) -> None:
        self.key = key


class FakeBatch:
    def __init__(self, documents: dict[str, dict[str, int]]) -> None:
        self._documents = documents
        self._writes: list[tuple[str, dict[str, object], bool]] = []

    def set(self, ref: FakeReference, data: dict[str, object], merge: bool) -> None:
        self._writes.append((ref.key, data, merge))

    async def commit(self) -> None:
        for key, data, merge in self._writes:
            assert merge
            document = self._documents.setdefault(key, {})
            for field, increment in data.items():
                document[field] = document.get(field, 0) + increment.value  # type: ignore[attr-defined]


class FakeCollection:
    def document(self, key: str) -> FakeReference:
        return FakeReference(key)


class FakeFirestore:
    def __init__(self) -> None:
        self.documents: dict[str, dict[str, int]] = {}
        self.collections: list[str] = []

    def collection(self, name: str) -> FakeCollection:
        self.collections.append(name)
        return FakeCollection()

    async def get_all(self, refs: list[FakeReference]) -> AsyncIterator[FakeSnapshot]:
        for ref in refs:
            yield FakeSnapshot(ref.key, self.documents.get(ref.key))

    def batch(self) -> FakeBatch:
        return FakeBatch(self.documents)


def firestore_store() -> tuple[FirestoreUsageStore, FakeFirestore]:
    fake = FakeFirestore()
    return FirestoreUsageStore("usage", cast(AsyncClient, fake)), fake


class TestFirestore:
    def test_reads_zero_from_missing_documents(self) -> None:
        store, _ = firestore_store()
        assert asyncio.run(store.spend(NOW)) == Spend()

    def test_records_atomic_increments_on_the_month_and_day_documents(self) -> None:
        store, fake = firestore_store()

        async def run() -> Spend:
            await store.record(NOW, micro_usd=1500, input_tokens=1000, output_tokens=100)
            await store.record(NOW, micro_usd=500, input_tokens=300, output_tokens=40)
            return await store.spend(NOW)

        assert asyncio.run(run()) == Spend(month_micro_usd=2000, day_micro_usd=2000)
        assert fake.documents["day-2026-09-21"] == {
            "micro_usd": 2000,
            "input_tokens": 1300,
            "output_tokens": 140,
            "questions": 2,
        }
        assert set(fake.documents) == {"month-2026-09", "day-2026-09-21"}
        assert set(fake.collections) == {"usage"}

    def test_a_new_day_starts_a_new_daily_total_inside_the_same_month(self) -> None:
        store, _ = firestore_store()

        async def run() -> Spend:
            await store.record(NOW, micro_usd=700, input_tokens=1, output_tokens=1)
            return await store.spend(NEXT_DAY)

        assert asyncio.run(run()) == Spend(month_micro_usd=700, day_micro_usd=0)


class TestBuild:
    def test_memory_is_the_default_store(self) -> None:
        assert isinstance(build_usage_store(Settings()), InMemoryUsageStore)

    def test_firestore_is_built_with_the_configured_collection(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        created: list[str] = []

        class Recorder:
            def __init__(self, collection: str) -> None:
                created.append(collection)

        monkeypatch.setattr(usage, "FirestoreUsageStore", Recorder)

        build_usage_store(Settings(usage_store="firestore", usage_collection="spend"))

        assert created == ["spend"]
