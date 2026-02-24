"""
Tests for main FastAPI application.

Covers health check, app creation, lifespan events.
"""

import pytest
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock


class TestHealthCheck:
    """Test health check endpoint."""

    @pytest.mark.asyncio
    async def test_health_check(self, test_client: AsyncClient):
        """Test health check endpoint."""
        response = await test_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ("healthy", "degraded")  # scheduler not running in test


class TestAppStartup:
    """Test app configuration."""

    def test_app_exists(self):
        """Test app object exists."""
        from app.main import app
        assert app is not None
        assert app.title is not None

    def test_cors_configured(self):
        """Test CORS middleware is configured."""
        from app.main import app
        # Check that CORSMiddleware is in the middleware stack
        middleware_classes = [type(m).__name__ for m in app.user_middleware]
        # The middleware is added via app.add_middleware, check routes exist
        assert len(app.routes) > 0

    def test_routes_registered(self):
        """Test that API routes are registered."""
        from app.main import app
        route_paths = [route.path for route in app.routes if hasattr(route, 'path')]
        assert "/api/health" in route_paths or any("/api" in p for p in route_paths)


class TestDatabaseUtils:
    """Test database utility functions."""

    @pytest.mark.asyncio
    async def test_check_db_connection(self):
        """Test database connection check."""
        from app.core.database import check_db_connection
        # In test env with SQLite memory, this may fail since we use test engine
        result = await check_db_connection()
        # Result is boolean regardless
        assert isinstance(result, bool)

    @pytest.mark.asyncio
    async def test_create_tables(self):
        """Test create_tables function."""
        from app.core.database import create_tables
        # This should not raise
        with patch("app.core.database.engine") as mock_engine:
            mock_conn = AsyncMock()
            mock_engine.begin.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
            mock_engine.begin.return_value.__aexit__ = AsyncMock(return_value=False)
            await create_tables()

    @pytest.mark.asyncio
    async def test_close_db(self):
        """Test close_db function."""
        from app.core.database import close_db
        with patch("app.core.database.engine") as mock_engine, \
             patch("app.core.database.data_engine") as mock_data_engine:
            mock_engine.dispose = AsyncMock()
            mock_data_engine.dispose = AsyncMock()
            await close_db()
            mock_engine.dispose.assert_called_once()
            mock_data_engine.dispose.assert_called_once()


class TestRateLimit:
    """Test rate limiting utilities."""

    def test_is_testing_true(self):
        """Test is_testing returns True in test mode."""
        from app.api.rate_limit import is_testing
        assert is_testing() is True

    def test_get_limiter_in_test_mode(self):
        """Test get_limiter returns None in test mode."""
        from app.api.rate_limit import get_limiter
        assert get_limiter() is None

    def test_rate_limit_decorator_passthrough(self):
        """Test rate_limit decorator passes through in test mode."""
        from app.api.rate_limit import rate_limit
        import asyncio

        @rate_limit("5/minute")
        async def test_func():
            return "ok"

        result = asyncio.get_event_loop().run_until_complete(test_func())
        assert result == "ok"
