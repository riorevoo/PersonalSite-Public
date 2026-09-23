# AI Personal Site Template

> This repository is an automatically generated public copy of a private repository. Direct
> changes here may be overwritten by the next successful private build.

See the live project at [riorevoo.com](https://riorevoo.com).

This is a chat-style personal website. Visitors can ask questions about the site owner, and the
answering service responds only from the information the owner has chosen to provide.

## Stack

- React, TypeScript and Vite frontend
- FastAPI and Python backend
- Pluggable stub or Anthropic answering engine
- Markdown knowledge base
- Playwright, Vitest and pytest test suites
- Firebase Hosting and Google Cloud Run deployment examples

## Make it yours

1. Replace every `TODO(owner)` entry under `backend/knowledge/`.
2. Edit `frontend/src/content/profile.ts` and `frontend/index.html`.
3. Replace `frontend/public/minime.png`, `frontend/public/favicon.png`, and the sample resume.
4. Copy the example environment files and configure your own domain, cloud project and API key.
5. Run `uv run --no-project python scripts/launch_check.py` before a production deployment.

The included placeholder content is deliberately rejected in production until it is completed.

## Local development

Prerequisites: Node.js 20.19+ and [uv](https://docs.astral.sh/uv/).

```bash
cd backend
uv sync
uv run fastapi dev app/main.py
```

In another terminal:

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

## Checks

```bash
uv run --no-project python scripts/check.py
```

This runs linting, formatting checks, strict typing, backend and frontend coverage, builds,
accessibility checks and browser tests.

## Deployment

The example deployment uses Firebase Hosting in front of a Cloud Run API. Read
`docs/deploy.md`, replace every example identifier, and keep all credentials in GitHub secrets or
your cloud secret manager.

