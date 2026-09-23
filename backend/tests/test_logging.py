import json
import logging
import sys

from app.core.logging import JsonFormatter, configure_logging


def record(message: str = "hello", **extra: object) -> logging.LogRecord:
    rec = logging.LogRecord("app.test", logging.INFO, __file__, 1, message, (), None)
    rec.__dict__.update(extra)
    return rec


class TestJsonFormatter:
    def test_emits_one_json_object_with_the_standard_fields(self) -> None:
        entry = json.loads(JsonFormatter().format(record("hello")))

        assert entry["message"] == "hello"
        assert entry["level"] == "INFO"
        assert entry["severity"] == "INFO"
        assert entry["logger"] == "app.test"
        assert entry["ts"].endswith("+00:00")

    def test_includes_extra_fields_but_not_logging_internals(self) -> None:
        entry = json.loads(JsonFormatter().format(record(status=200, path="/api/chat")))

        assert entry["status"] == 200
        assert entry["path"] == "/api/chat"
        assert "levelno" not in entry
        assert "pathname" not in entry
        assert "args" not in entry

    def test_formats_message_arguments(self) -> None:
        rec = logging.LogRecord("app.test", logging.INFO, __file__, 1, "%d items", (3,), None)
        assert json.loads(JsonFormatter().format(rec))["message"] == "3 items"

    def test_survives_values_json_cannot_encode(self) -> None:
        entry = json.loads(JsonFormatter().format(record(thing=object())))
        assert entry["thing"].startswith("<object object")

    def test_includes_a_traceback(self) -> None:
        try:
            raise ValueError("bad")
        except ValueError:
            rec = logging.LogRecord(
                "app.test", logging.ERROR, __file__, 1, "failed", (), sys.exc_info()
            )
        entry = json.loads(JsonFormatter().format(rec))
        assert "ValueError: bad" in entry["exception"]


class TestConfigureLogging:
    def test_is_idempotent_and_sets_the_level(self) -> None:
        logger = logging.getLogger("app")
        before = len(logger.handlers)

        configure_logging("WARNING")
        configure_logging("WARNING")
        json_handlers = [h for h in logger.handlers if getattr(h, "_app_json", False)]

        assert len(json_handlers) == 1
        assert len(logger.handlers) <= before + 1
        assert logger.level == logging.WARNING
        assert isinstance(json_handlers[0].formatter, JsonFormatter)
        configure_logging("INFO")
