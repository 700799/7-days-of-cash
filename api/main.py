"""FastAPI application entrypoint.

Schema initialization is intentionally NOT called at app startup — on Vercel
that would run on every cold start and slow each lambda boot. Instead,
``scripts/migrate.py`` is run once after deploy. The connection pool is created
lazily on first DB call.
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from .config import get_settings
from .db import reset_pool
from .routes import alerts as alerts_routes
from .routes import auth as auth_routes
from .routes import billing as billing_routes
from .routes import cron as cron_routes
from .routes import movers as movers_routes
from .routes import news as news_routes
from .routes import preferences as preferences_routes
from .routes import screener as screener_routes
from .routes import tickers as tickers_routes
from .security import (
    allowed_origins,
    body_size_limit_middleware,
    limiter,
    rate_limit_handler,
)


@asynccontextmanager
async def _lifespan(app: FastAPI):
    """Lifespan handler: the pool is built lazily on first use, so startup is
    a no-op. On shutdown we tear it down so test runs leave no dangling sockets.
    """
    yield
    try:
        reset_pool()
    except Exception:
        pass


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Best7DaysMula API", version="0.1.0", lifespan=_lifespan)

    # Rate limiter — per-user (cookie) when logged in, else per-IP. See security.py.
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, rate_limit_handler)

    # Body size cap — reject >64KB before pydantic / DB touch it.
    app.middleware("http")(body_size_limit_middleware)

    # CORS — strict allowlist (never `*` with credentials).
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins(),
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
        max_age=3600,
    )

    # Authlib uses Starlette's session for OAuth state during the redirect dance.
    # On Vercel this is cookie-backed, not server-side, so it still works statelessly.
    app.add_middleware(SessionMiddleware, secret_key=settings.SESSION_SECRET, same_site="lax")

    app.include_router(auth_routes.router)
    app.include_router(tickers_routes.router)
    app.include_router(news_routes.router)
    app.include_router(screener_routes.router)
    app.include_router(movers_routes.router)
    app.include_router(preferences_routes.router)
    app.include_router(cron_routes.router)
    app.include_router(billing_routes.router)
    app.include_router(alerts_routes.router)

    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    return app


app = create_app()
