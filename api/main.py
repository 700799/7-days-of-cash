"""FastAPI application entrypoint."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from .config import get_settings
from .db import init_schema
from .routes import auth as auth_routes
from .routes import news as news_routes
from .routes import screener as screener_routes
from .routes import tickers as tickers_routes


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Best7DaysMula API", version="0.1.0")

    init_schema()

    origins = list({"http://localhost:3000", settings.FRONTEND_URL})
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Authlib uses Starlette's session for OAuth state during the redirect dance.
    app.add_middleware(SessionMiddleware, secret_key=settings.SESSION_SECRET, same_site="lax")

    app.include_router(auth_routes.router)
    app.include_router(tickers_routes.router)
    app.include_router(news_routes.router)
    app.include_router(screener_routes.router)

    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    return app


app = create_app()
