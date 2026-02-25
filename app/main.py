"""
FastAPI application main entry point.

Initializes and configures the FastAPI application with all routes,
middleware, and startup/shutdown events.
"""

import os
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger

from app.api import api_router
from app.core.config import settings
from app.core.database import init_db, close_db
from app.services.scheduler import task_scheduler


# Check if we're in testing mode
TESTING = os.getenv("TESTING", "false").lower() == "true"

# Configure loguru logging (file rotation + level from settings)
import sys
logger.remove()  # Remove default stderr handler
logger.add(sys.stderr, level=settings.log_level, format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>")
if not TESTING:
    Path(settings.log_file).parent.mkdir(parents=True, exist_ok=True)
    logger.add(
        settings.log_file,
        rotation="10 MB",
        retention="30 days",
        compression="gz",
        level=settings.log_level,
        encoding="utf-8",
    )

# Initialize rate limiter (only in production)
from app.api.rate_limit import get_limiter
limiter = get_limiter()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan manager.

    Handles startup and shutdown events.
    """
    # Startup
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    logger.info(f"Environment: {settings.app_env}")

    # Security warning
    if settings.secret_key == "change-this-secret-key":
        logger.warning("⚠️  USING DEFAULT SECRET KEY! Change this in production!")

    # Initialize database
    from app.core.database import create_tables

    await create_tables()
    await init_db()

    # Start task scheduler
    await task_scheduler.start()

    logger.info("Application startup complete")

    yield

    # Shutdown
    logger.info("Shutting down application...")
    await task_scheduler.shutdown()
    await close_db()
    logger.info("Application shutdown complete")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    description="Web-based financial data management platform for akshare",
    version=settings.app_version,
    docs_url="/docs" if settings.app_debug else None,
    redoc_url="/redoc" if settings.app_debug else None,
    lifespan=lifespan,
)

# Attach rate limiter to app state (required by slowapi)
if limiter is not None:
    app.state.limiter = limiter

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
)

# Request logging middleware (skip in testing to reduce noise)
if not TESTING:
    from app.middleware.request_logging import RequestLoggingMiddleware
    app.add_middleware(RequestLoggingMiddleware)

# Rate limit exception handler (only in production)
if not TESTING:
    from slowapi.errors import RateLimitExceeded

    @app.exception_handler(RateLimitExceeded)
    async def rate_limit_handler(request, exc):
        """Handle rate limit exceeded exceptions."""
        return JSONResponse(
            status_code=429,
            content={"detail": "Rate limit exceeded. Please try again later."},
        )


# Global exception handlers for structured error responses
@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    """Handle ValueError with structured response."""
    logger.warning(f"ValueError: {exc}")
    return JSONResponse(
        status_code=400,
        content={"success": False, "message": str(exc), "error_code": "VALUE_ERROR"},
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """Handle uncaught exceptions with structured response."""
    logger.error(f"Unhandled exception: {type(exc).__name__}: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": "Internal server error",
            "error_code": "INTERNAL_ERROR",
        },
    )


# Include API routes (v1 is the canonical prefix, /api kept for backward compatibility)
app.include_router(api_router, prefix="/api/v1")
app.include_router(api_router, prefix="/api")


@app.get("/health")
async def health_check():
    """
    Health check endpoint.

    Returns application health status.
    """
    from app.core.database import check_db_connection

    db_healthy = await check_db_connection()
    scheduler_running = task_scheduler.is_running

    # Determine overall status
    if db_healthy and scheduler_running:
        overall_status = "healthy"
    elif db_healthy:
        overall_status = "degraded"  # Scheduler not running
    else:
        overall_status = "unhealthy"

    return {
        "status": overall_status,
        "app_name": settings.app_name,
        "version": settings.app_version,
        "environment": settings.app_env,
        "checks": {
            "database": "connected" if db_healthy else "disconnected",
            "scheduler": "running" if scheduler_running else "stopped",
        },
        "timestamp": datetime.now(UTC).isoformat(),
    }


# Serve Vue frontend static files
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend" / "dist"

if FRONTEND_DIR.is_dir():
    # Mount static assets directory
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIR / "assets"), name="static-assets")

    @app.get("/")
    async def serve_index():
        """Serve Vue SPA index page."""
        return FileResponse(FRONTEND_DIR / "index.html")

    @app.exception_handler(404)
    async def spa_not_found(request: Request, exc):
        """Serve index.html for SPA client-side routing on 404."""
        # Only serve SPA for non-API paths
        path = request.url.path
        if path.startswith(("/api/", "/docs", "/redoc", "/openapi", "/health")):
            return JSONResponse(status_code=404, content={"detail": "Not Found"})
        # Try to serve static file first
        file_path = FRONTEND_DIR / path.lstrip("/")
        if file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(FRONTEND_DIR / "index.html")
else:
    @app.get("/")
    async def root():
        """Root endpoint with basic information."""
        return {
            "app_name": settings.app_name,
            "version": settings.app_version,
            "description": "Web-based financial data management platform for akshare",
            "docs": "/docs" if settings.app_debug else None,
        }
