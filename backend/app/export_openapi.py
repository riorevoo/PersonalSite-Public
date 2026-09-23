"""Write the API's OpenAPI schema to backend/openapi.json.

That file is the contract the frontend types are generated from (`npm run types:generate`).
Regenerate it after changing any request or response model:

    uv run python -m app.export_openapi
"""

import json
from pathlib import Path

from app.main import create_app

OPENAPI_PATH = Path(__file__).resolve().parent.parent / "openapi.json"


def render() -> str:
    return json.dumps(create_app().openapi(), indent=2, sort_keys=True) + "\n"


def main() -> None:
    OPENAPI_PATH.write_text(render(), encoding="utf-8")
    print(f"wrote {OPENAPI_PATH}")


if __name__ == "__main__":
    main()
