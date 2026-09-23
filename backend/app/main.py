from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import cast

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import Settings, get_settings
from app.core.logging import configure_logging
from app.core.middleware import (
    BodySizeLimitMiddleware,
    RequestLoggingMiddleware,
    SecurityHeadersMiddleware,
)
from app.core.rate_limit import RateLimiter, RateLimitMiddleware, Rule
from app.services.runtime import AppServices


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Load the knowledge base up front, so a broken post or (in production) a placeholder stops
    the app from starting instead of surprising the first visitor."""
    cast(AppServices, app.state.services).initialize()
    yield


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the app. Pass `settings` to override the environment (used by tests)."""
    settings = settings or get_settings()
    configure_logging(settings.log_level)
    production = settings.env == "production"

    app = FastAPI(
        title="Personal Site API",
        version="0.1.0",
        # The interactive docs and schema are for development; production exposes only the API.
        docs_url=None if production else "/docs",
        redoc_url=None if production else "/redoc",
        openapi_url=None if production else "/openapi.json",
        lifespan=lifespan,
    )
    app.state.services = AppServices(settings)
    app.dependency_overrides[get_settings] = lambda: settings
    app.include_router(api_router)

    limiter = RateLimiter(
        [
            Rule(limit=settings.rate_limit_per_minute, window_seconds=60),
            Rule(limit=settings.rate_limit_per_day, window_seconds=24 * 60 * 60),
        ]
    )
    app.state.rate_limiter = limiter

    # Each add_middleware wraps the ones added before it, so the LAST one here runs FIRST:
    # log everything, add headers, apply CORS (so 413/429 responses stay readable by the browser),
    # rate-limit, then cap the body size, then the app.
    app.add_middleware(BodySizeLimitMiddleware, max_bytes=settings.max_body_bytes)
    app.add_middleware(
        RateLimitMiddleware, limiter=limiter, trusted_proxy_hops=settings.trusted_proxy_hops
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )
    app.add_middleware(SecurityHeadersMiddleware, hsts=production)
    app.add_middleware(RequestLoggingMiddleware)
    return app


app = create_app()
