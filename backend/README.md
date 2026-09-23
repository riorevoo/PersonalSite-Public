# Personal Site: Backend

FastAPI service behind the chat-style personal site. It exposes a small JSON API that the
frontend calls to answer visitors' questions **about the site's owner only**.

The answering engine is intentionally pluggable: today a `StubAnswerer` returns canned
answers for the suggestion chips and an honest fallback for everything else. The real
engine (LLM API vs. self-trained model / RAG) is tracked in epic PS-5.

## Requirements

- [uv](https://docs.astral.sh/uv/) (manages Python and dependencies)
- Python 3.12+ (uv will fetch one if needed; `.python-version` pins 3.14 locally)

## Setup

```bash
cd backend
uv sync                 # creates backend/.venv and installs deps + dev tools
cp .env.example .env    # optional; defaults work for local dev
```

## Run

```bash
uv run fastapi dev app/main.py        # http://localhost:8000, auto-reload
```

- Interactive docs: http://localhost:8000/docs
- Health check: `curl http://localhost:8000/api/health` → `{"status":"ok"}`

Production-style: `uv run fastapi run app/main.py --port 8000`.

## Test & lint

```bash
uv run pytest                    # tests + coverage report; fails below 90% (branch coverage on)
uv run mypy                      # strict type checking of app/ and tests/
uv run ruff check .              # lint
uv run ruff format --check .     # formatting check (drop --check to fix)
```

All four must pass before a change is done. Coverage is enforced by default (`addopts` in
`pyproject.toml`), so plain `uv run pytest` fails if new code ships without tests. Raise
`fail_under` when coverage sits well above it; do not lower it quietly.

To test a route against a different engine, use the `answerer_override` fixture in
`tests/conftest.py` (it swaps the `Answerer` dependency for a recording fake).
Use `with TestClient(create_app(settings)) as client:` to exercise startup validation. Knowledge
and engine instances belong to that app and are initialized using its settings at startup.

## API

| Method | Path          | Body                                   | Response            |
|--------|---------------|----------------------------------------|---------------------|
| GET    | `/api/health` | (none)                                 | `{"status": "ok"}`  |
| POST   | `/api/chat`   | `{"message": str, "history": [Turn]}`  | `{"answer": str}`   |

`Turn` is `{"role": "user" | "assistant", "content": str}`, oldest first.

Limits (all return **422**): a blank message, a message longer than `APP_MAX_MESSAGE_CHARS`
(default 500), more than 20 history turns, or a history turn longer than 4000 characters.

Errors use FastAPI's shape, `{"detail": "..."}` (a list for schema validation errors). The frontend
treats any non-2xx as a failure and shows a friendly message with a retry button.

### The contract file

`backend/openapi.json` is the committed OpenAPI schema. The frontend generates its TypeScript
types from it (`npm run types:generate` in `frontend/`), so the two cannot drift silently.
After changing any request or response model:

```bash
uv run python -m app.export_openapi     # rewrite backend/openapi.json
cd ../frontend && npm run types:generate
```

`tests/test_contract.py` fails if `openapi.json` is stale.

## Knowledge base

Everything the site may say about its owner is Markdown in `backend/knowledge/` (profile,
experience, projects, skills, interests, faq, boundaries). `app/services/knowledge.py` loads it:
YAML front matter, `## ` sections as chunks, HTML comments dropped, `faq.md` headings matched
against visitor questions (the model answers first; a matching entry is the fallback when it cannot). **Read `knowledge/README.md` for the writing guide.**

- Unfinished text is marked `TODO(owner)`. The app logs a warning for each while developing and
  refuses to start with `APP_ENV=production` until they are gone.
- To keep real content out of the repository, point `APP_KNOWLEDGE_DIR` at another folder.
- A test checks that every suggestion chip on the page has a matching entry in `faq.md`.

## Answering engines

`Answerer.answer` is async, so real engines can await network calls. Engines are registered in
`ENGINES` in `app/services/answerer.py` and chosen with `APP_ANSWERER` (currently only `stub`,
which answers the suggestion chips with placeholder text). Each app builds its engine once and
reuses it; separately configured apps do not share engines or knowledge.
To add one: implement the protocol, add it to `ENGINES`, and add its name to the `Literal` in
`Settings.answerer` so a typo fails at startup.

## Security and limits

- **Rate limiting:** `POST /api/chat` allows 10 questions per minute and 100 per day per visitor
  (`APP_RATE_LIMIT_PER_MINUTE`, `APP_RATE_LIMIT_PER_DAY`). Over the limit the API answers **429**
  with a `Retry-After` header, before the request body is even read; the site shows a friendly
  message. Counters live in memory, which is right for a single process (a free host runs one).
- **Behind a proxy:** set `APP_TRUSTED_PROXY_HOPS` to the exact number of reverse proxies in front
  of the app (Render's load balancer is 1; add 1 for Cloudflare in front of that). The visitor's
  address is then read from the right end of `X-Forwarded-For`, so a visitor cannot fake it. Leave it
  `0` when the app is reached directly. A wrong value either lumps every visitor together or lets
  them dodge the limit.
- **Body size:** requests over `APP_MAX_BODY_BYTES` (256 KB) get **413**, including bodies streamed
  without a declared length.
- **Headers:** every response carries `X-Content-Type-Options`, `Referrer-Policy` and
  `Cache-Control: no-store`; API responses add a lock-down `Content-Security-Policy`; production adds
  `Strict-Transport-Security`.
- **Production guards** (`APP_ENV=production`): `/docs`, `/redoc` and `/openapi.json` are off, the app
  refuses to start if `APP_CORS_ORIGINS` is a wildcard or localhost, and refuses to start while the
  knowledge base still has `TODO(owner)` placeholders.
- **Secrets:** API keys (once an engine needs one) go only in `backend/.env` or the host's
  environment, never in the frontend, which only ever sees `VITE_*` public settings.

### Logging

One JSON line per request on stderr (logger `app.access`): request id, method, path, status,
duration in ms, and for chat the engine, message length and history length. **Visitors' text is never
logged.** Every response carries `X-Request-ID` (a valid one sent by the client is echoed, otherwise
one is generated) so a failure report can be matched to a log line. Health checks log at DEBUG.
Set the level with `APP_LOG_LEVEL`.

## Configuration

Environment variables (or `backend/.env`), all prefixed `APP_`:

| Variable                    | Default                     | Purpose                                   |
|-----------------------------|-----------------------------|-------------------------------------------|
| `APP_ENV`                   | `development`               | `development` / `production` / `test`     |
| `APP_LOG_LEVEL`             | `INFO`                      | `DEBUG` / `INFO` / `WARNING` / `ERROR`    |
| `APP_CORS_ORIGINS`          | `["http://localhost:5173"]` | JSON list of allowed origins (real site origin in production) |
| `APP_MAX_MESSAGE_CHARS`     | `500`                       | Max visitor message length                |
| `APP_MAX_BODY_BYTES`        | `262144`                    | Max request body size                     |
| `APP_RATE_LIMIT_PER_MINUTE` | `10`                        | Questions per visitor per minute          |
| `APP_RATE_LIMIT_PER_DAY`    | `100`                       | Questions per visitor per day             |
| `APP_TRUSTED_PROXY_HOPS`    | `0`                         | Reverse proxies in front of the app       |
| `APP_ANSWERER`              | `stub`                      | Which answering engine to use             |
| `APP_KNOWLEDGE_DIR`         | `backend/knowledge`         | Folder of Markdown knowledge files        |

## Layout

```
app/
  main.py               create_app() factory: middleware stack + routers
  core/config.py        Settings (pydantic-settings) and production guards
  core/rate_limit.py    sliding-window limiter, client address, 429 middleware
  core/middleware.py    body size cap, security headers, request logging
  core/logging.py       JSON log formatter
  api/router.py         mounts all routes under /api
  api/routes/           health.py, chat.py
  schemas/              request/response models (chat.py, health.py): the API contract
  services/answerer.py  Answerer protocol, engine registry, StubAnswerer  <- add engines here
  services/knowledge.py loads and chunks the Markdown knowledge base
  export_openapi.py     writes openapi.json (source of the frontend types)
knowledge/              the owner's content (see knowledge/README.md)
openapi.json            the committed contract
tests/                  pytest + TestClient
```
