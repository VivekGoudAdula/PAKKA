"""
Pakka API — FastAPI application entry point.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db import init_db
from app.events.hub import router as events_router
from app.routers.api import router as api_router
from app.routers.health import router as health_router
from app.voice.exotel_ws import router as exotel_router

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan — startup and shutdown hooks."""
    logger.info("Pakka API starting", env=settings.app_env)
    init_db()
    yield
    logger.info("Pakka API shutting down")


def create_app() -> FastAPI:
    """Factory that creates and configures the FastAPI application."""
    app = FastAPI(
        title="Pakka API",
        description=(
            "Voice assistant API for small Indian service businesses. "
            "Answers calls, books jobs, dispatches technicians, chases payments."
        ),
        version="0.1.0",
        lifespan=lifespan,
        # Disable docs in production
        docs_url="/docs" if settings.app_env != "production" else None,
        redoc_url="/redoc" if settings.app_env != "production" else None,
    )

    # ── CORS ─────────────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Routers ───────────────────────────────────────────────────────────────
    app.include_router(health_router)
    app.include_router(events_router)
    app.include_router(exotel_router)
    app.include_router(api_router)

    return app


app = create_app()
