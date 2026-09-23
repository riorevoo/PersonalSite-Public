import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import usage_report  # noqa: E402

from app.core.config import Settings  # noqa: E402

NOW = datetime(2026, 9, 21, 12, 0, tzinfo=UTC)


class FakeSnapshot:
    def __init__(self, data: dict[str, int] | None) -> None:
        self.exists = data is not None
        self._data = data or {}

    def to_dict(self) -> dict[str, int]:
        return self._data


class FakeDocument:
    def __init__(self, data: dict[str, int] | None) -> None:
        self._data = data

    def get(self) -> FakeSnapshot:
        return FakeSnapshot(self._data)


class FakeCollection:
    def __init__(self, documents: dict[str, dict[str, int]]) -> None:
        self._documents = documents

    def document(self, key: str) -> FakeDocument:
        return FakeDocument(self._documents.get(key))


class FakeClient:
    def __init__(self, documents: dict[str, dict[str, int]]) -> None:
        self.documents = documents
        self.collections: list[str] = []

    def collection(self, name: str) -> Any:
        self.collections.append(name)
        return FakeCollection(self.documents)


DOCUMENTS = {
    "month-2026-09": {
        "micro_usd": 830_000,
        "questions": 61,
        "input_tokens": 141_000,
        "output_tokens": 9_200,
    },
    "day-2026-09-21": {
        "micro_usd": 90_000,
        "questions": 12,
        "input_tokens": 30_000,
        "output_tokens": 2_000,
    },
    "day-2026-09-20": {
        "micro_usd": 45_500,
        "questions": 6,
        "input_tokens": 1_000,
        "output_tokens": 500,
    },
}


def test_reports_the_month_against_its_budget_and_recent_days() -> None:
    client = FakeClient(DOCUMENTS)

    lines = usage_report.report(client, Settings(), NOW, days=3)

    assert (
        lines[0]
        == "Month 2026-09: $0.8300 of $1.50 (55%), 61 questions, 141,000 tokens in, 9,200 out"
    )
    assert (
        lines[1]
        == "Today 2026-09-21: $0.0900 of $0.30 (30%), 12 questions, 30,000 tokens in, 2,000 out"
    )
    assert lines[2] == "      2026-09-20: $0.0455, 6 questions, 1,000 tokens in, 500 out"
    assert lines[3] == "      2026-09-19: $0.0000, 0 questions, 0 tokens in, 0 out"


def test_uses_the_configured_collection_and_budgets() -> None:
    client = FakeClient({})

    lines = usage_report.report(
        client, Settings(usage_collection="spend", monthly_budget_usd=2), NOW, 1
    )

    assert set(client.collections) == {"spend"}
    assert lines[0].startswith("Month 2026-09: $0.0000 of $2.00 (0%)")


def test_main_prints_the_report(capsys: pytest.CaptureFixture[str]) -> None:
    assert usage_report.main(["--days", "1"], client=FakeClient(DOCUMENTS)) == 0

    output = capsys.readouterr().out.splitlines()
    assert len(output) == 2
    assert output[0].startswith("Month 2026-")


def test_main_lists_at_least_one_day(capsys: pytest.CaptureFixture[str]) -> None:
    usage_report.main(["--days", "0"], client=FakeClient({}))

    assert len(capsys.readouterr().out.splitlines()) == 2
