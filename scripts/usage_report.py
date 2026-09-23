"""Print what the chat assistant has cost this month, from the counters in Firestore.

Run it from `backend/`, after signing in once with `gcloud auth application-default login`:

    cd backend
    uv run python ../scripts/usage_report.py --project YOUR_GCP_PROJECT
    uv run python ../scripts/usage_report.py --project YOUR_GCP_PROJECT --days 14

The counters hold only totals (dollars, tokens, question counts), never visitor text. The spend
figures are estimates from the token counts the API reports; the Anthropic console is the source
of truth for billing.
"""

import argparse
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Protocol

# Running a file puts scripts/ (not the current folder) on the import path, so add the backend.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.core.config import Settings
from app.services.usage import day_key, month_key

MICRO = 1_000_000


class Client(Protocol):
    def collection(self, name: str) -> Any: ...


def read_counters(client: Client, collection: str, key: str) -> dict[str, int]:
    snapshot = client.collection(collection).document(key).get()
    if not snapshot.exists:
        return {}
    return {name: int(value) for name, value in snapshot.to_dict().items()}


def line(label: str, counters: dict[str, int], budget_usd: float | None) -> str:
    spent = counters.get("micro_usd", 0) / MICRO
    text = f"{label}: ${spent:.4f}"
    if budget_usd:
        text += f" of ${budget_usd:.2f} ({spent / budget_usd:.0%})"
    text += f", {counters.get('questions', 0)} questions"
    tokens_in, tokens_out = counters.get("input_tokens", 0), counters.get("output_tokens", 0)
    return f"{text}, {tokens_in:,} tokens in, {tokens_out:,} out"


def report(client: Client, settings: Settings, now: datetime, days: int) -> list[str]:
    collection = settings.usage_collection
    lines = [
        line(
            f"Month {now:%Y-%m}",
            read_counters(client, collection, month_key(now)),
            settings.monthly_budget_usd,
        )
    ]
    for offset in range(days):
        moment = now - timedelta(days=offset)
        budget = settings.daily_budget_usd if offset == 0 else None
        label = "Today " if offset == 0 else "      "
        lines.append(
            line(
                f"{label}{moment:%Y-%m-%d}",
                read_counters(client, collection, day_key(moment)),
                budget,
            )
        )
    return lines


def main(argv: list[str] | None = None, client: Client | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("--project", help="Google Cloud project id (default: the gcloud default)")
    parser.add_argument("--days", type=int, default=7, help="how many recent days to list")
    args = parser.parse_args(argv)

    if client is None:
        from google.cloud import firestore  # imported late: only needed for a real run

        client = firestore.Client(project=args.project)
    print("\n".join(report(client, Settings(), datetime.now(UTC), max(args.days, 1))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
