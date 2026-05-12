"""
FastAPI application entry point.
Configures CORS, Sentry, exception handlers, ML scheduler,
Redis lifecycle, and mounts all API routers.
"""

import logging
from contextlib import asynccontextmanager

import sentry_sdk
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.exceptions import register_exception_handlers

settings = get_settings()

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# ── Sentry ───────────────────────────────────────────────────────────────────
if settings.SENTRY_DSN:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.ENVIRONMENT,
        traces_sample_rate=0.2,
        profiles_sample_rate=0.1,
    )
    logger.info("Sentry initialized for environment: %s", settings.ENVIRONMENT)


# ── Lifespan ─────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events."""
    logger.info("Starting %s v%s (%s)", settings.APP_NAME, settings.APP_VERSION, settings.ENVIRONMENT)

    # Start ML scheduler
    try:
        from app.ml.scheduler import start_scheduler
        start_scheduler()
        logger.info("ML scheduler started successfully")
    except Exception as e:
        logger.warning("ML scheduler failed to start: %s (non-fatal)", e)

    # Initialize Redis connection
    try:
        from app.core.redis import get_redis
        await get_redis()
        logger.info("Redis connection established")
    except Exception as e:
        logger.warning("Redis connection failed: %s (caching disabled)", e)

    yield

    # Shutdown
    logger.info("Shutting down %s", settings.APP_NAME)

    # Stop ML scheduler
    try:
        from app.ml.scheduler import stop_scheduler
        stop_scheduler()
    except Exception as e:
        logger.warning("ML scheduler shutdown error: %s", e)

    # Close Redis
    try:
        from app.core.redis import close_redis
        await close_redis()
    except Exception as e:
        logger.warning("Redis close error: %s", e)

    # Close database connections
    from app.db.session import engine
    await engine.dispose()
    logger.info("All connections closed — shutdown complete")


# ── App Factory ──────────────────────────────────────────────────────────────
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI-Powered Vendor Food Demand Forecasting & Analytics Platform API",
    docs_url="/docs" if settings.DEBUG or settings.ENVIRONMENT != "production" else None,
    redoc_url="/redoc" if settings.DEBUG or settings.ENVIRONMENT != "production" else None,
    lifespan=lifespan,
)

# ── CORS ─────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Exception Handlers ──────────────────────────────────────────────────────
register_exception_handlers(app)

# ── Routers ──────────────────────────────────────────────────────────────────
from app.api.auth import router as auth_router
from app.api.menu import router as menu_router
from app.api.orders import router as orders_router
from app.api.forecasts import forecast_router, ml_router
from app.api.analytics import router as analytics_router
from app.api.chat import router as chat_router

app.include_router(auth_router, prefix="/api/v1")
app.include_router(menu_router, prefix="/api/v1")
app.include_router(orders_router, prefix="/api/v1")
app.include_router(forecast_router, prefix="/api/v1")
app.include_router(ml_router, prefix="/api/v1")
app.include_router(analytics_router, prefix="/api/v1")
app.include_router(chat_router, prefix="/api/v1")


# ── Health Check ─────────────────────────────────────────────────────────────
@app.get("/health", tags=["System"])
async def health_check():
    """Health check endpoint for load balancers and monitoring."""
    # Check Redis connectivity
    redis_status = "unknown"
    try:
        from app.core.redis import get_redis
        client = await get_redis()
        await client.ping()
        redis_status = "connected"
    except Exception:
        redis_status = "disconnected"

    # Check scheduler status
    scheduler_status = "unknown"
    try:
        from app.ml.scheduler import get_scheduler_status
        sched = get_scheduler_status()
        scheduler_status = "running" if sched["running"] else "stopped"
    except Exception:
        scheduler_status = "unavailable"

    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "services": {
            "redis": redis_status,
            "ml_scheduler": scheduler_status,
        },
    }


@app.get("/", tags=["System"])
async def root():
    """Root endpoint with API information."""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "health": "/health",
    }
