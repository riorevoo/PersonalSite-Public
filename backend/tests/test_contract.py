"""The committed OpenAPI file is the contract the frontend types are generated from."""

import json
from pathlib import Path

import pytest

from app import export_openapi
from app.main import create_app


def test_committed_openapi_matches_the_app() -> None:
    committed = json.loads(export_openapi.OPENAPI_PATH.read_text(encoding="utf-8"))
    assert committed == create_app().openapi(), (
        "backend/openapi.json is stale. Run `uv run python -m app.export_openapi`, then "
        "`npm run types:generate` in frontend/, and commit both."
    )


def test_export_writes_the_rendered_schema(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    target = tmp_path / "openapi.json"
    monkeypatch.setattr(export_openapi, "OPENAPI_PATH", target)

    export_openapi.main()

    assert target.read_text(encoding="utf-8") == export_openapi.render()
    assert str(target) in capsys.readouterr().out


def test_chat_contract_shape() -> None:
    schemas = create_app().openapi()["components"]["schemas"]

    assert set(schemas["ChatRequest"]["properties"]) == {"message", "history"}
    assert schemas["ChatRequest"]["required"] == ["message"]
    assert set(schemas["ChatResponse"]["properties"]) == {"answer"}
    assert schemas["ChatTurn"]["properties"]["role"]["enum"] == ["user", "assistant"]
