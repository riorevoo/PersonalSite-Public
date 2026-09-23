"""Structured (JSON) logging: one line per event, machine-readable, no visitor text."""

import json
import logging
from datetime import UTC, datetime

# Attributes every LogRecord has; anything else on a record came from `extra=` and is logged.
_STANDARD_ATTRIBUTES = frozenset(
    logging.LogRecord("", 0, "", 0, "", (), None).__dict__.keys() | {"message", "asctime"}
)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        entry: dict[str, object] = {
            "ts": datetime.fromtimestamp(record.created, UTC).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            # Cloud Logging reads `severity`, so alerts can filter on it.
            "severity": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        entry.update({k: v for k, v in record.__dict__.items() if k not in _STANDARD_ATTRIBUTES})
        if record.exc_info:
            entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(entry, default=str)


def configure_logging(level: str) -> None:
    """Send the app's logs to stderr as JSON. Safe to call more than once."""
    logger = logging.getLogger("app")
    logger.setLevel(level)
    if not any(getattr(h, "_app_json", False) for h in logger.handlers):
        handler = logging.StreamHandler()
        handler.setFormatter(JsonFormatter())
        handler._app_json = True  # type: ignore[attr-defined]
        logger.addHandler(handler)
