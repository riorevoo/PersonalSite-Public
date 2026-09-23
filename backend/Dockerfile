# The API container (Cloud Run). Build from this folder: `docker build -t personal-site-api backend`.
# The frontend is not in here: it is a static build served by Firebase Hosting (see firebase.json).

FROM python:3.14-slim AS build
COPY --from=ghcr.io/astral-sh/uv:0.11.16 /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never
WORKDIR /app
# Dependencies first, so this layer is cached until pyproject.toml or uv.lock change.
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project
COPY app ./app
# The knowledge base is baked into the image: editing it means redeploying.
COPY knowledge ./knowledge

FROM python:3.14-slim
RUN useradd --system --create-home --uid 10001 app
WORKDIR /app
COPY --from=build --chown=app:app /app /app
# Secure by default: production mode refuses placeholders, localhost origins and open drafts.
# For a local trial run: docker run -e APP_ENV=development -p 8080:8080 personal-site-api
ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 APP_ENV=production
USER app
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s --start-period=15s \
  CMD python -c "import os, urllib.request; urllib.request.urlopen(f'http://127.0.0.1:{os.environ.get(\"PORT\", \"8080\")}/api/health', timeout=2)"
# One worker: rate limits are counted per process, and Cloud Run scales by adding instances.
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
