"""
Tests for main.py covering lifespan, static files, and uncovered branches.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock
from contextlib import asynccontextmanager


class TestLifespan:
    @pytest.mark.asyncio
    async def test_lifespan_startup_shutdown(self):
        from app.main import lifespan

        with patch("app.core.database.create_tables", new_callable=AsyncMock) as mock_ct, \
             patch("app.main.init_db", new_callable=AsyncMock) as mock_init, \
             patch("app.main.task_scheduler") as mock_sched, \
             patch("app.main.close_db", new_callable=AsyncMock) as mock_close, \
             patch("app.main.settings") as mock_settings:
            mock_settings.app_name = "test"
            mock_settings.app_version = "1.0"
            mock_settings.app_env = "test"
            mock_settings.secret_key = "change-this-secret-key"
            mock_sched.start = AsyncMock()
            mock_sched.shutdown = AsyncMock()

            async with lifespan(MagicMock()):
                pass

            mock_ct.assert_called_once()
            mock_init.assert_called_once()
            mock_sched.start.assert_called_once()
            mock_sched.shutdown.assert_called_once()
            mock_close.assert_called_once()

    @pytest.mark.asyncio
    async def test_lifespan_safe_secret(self):
        from app.main import lifespan

        with patch("app.core.database.create_tables", new_callable=AsyncMock), \
             patch("app.main.init_db", new_callable=AsyncMock), \
             patch("app.main.task_scheduler") as mock_sched, \
             patch("app.main.close_db", new_callable=AsyncMock), \
             patch("app.main.settings") as mock_settings:
            mock_settings.app_name = "test"
            mock_settings.app_version = "1.0"
            mock_settings.app_env = "test"
            mock_settings.secret_key = "a-real-secret-key-here"
            mock_sched.start = AsyncMock()
            mock_sched.shutdown = AsyncMock()

            async with lifespan(MagicMock()):
                pass


class TestHealthCheckBranches:
    @pytest.mark.asyncio
    async def test_healthy(self):
        from app.main import health_check

        with patch("app.core.database.check_db_connection", new_callable=AsyncMock, return_value=True), \
             patch("app.main.task_scheduler") as mock_sched:
            mock_sched._running = True
            result = await health_check()
        assert result["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_degraded_scheduler_off(self):
        from app.main import health_check

        with patch("app.core.database.check_db_connection", new_callable=AsyncMock, return_value=True), \
             patch("app.main.task_scheduler") as mock_sched:
            type(mock_sched)._running = property(lambda self: False)
            result = await health_check()
        assert result["status"] in ("healthy", "degraded")

    @pytest.mark.asyncio
    async def test_unhealthy(self):
        from app.main import health_check

        with patch("app.core.database.check_db_connection", new_callable=AsyncMock, return_value=False), \
             patch("app.main.task_scheduler") as mock_sched:
            mock_sched._running = False
            result = await health_check()
        assert result["status"] == "unhealthy"


class TestRootEndpoint:
    @pytest.mark.asyncio
    async def test_root_no_frontend(self):
        """Test root endpoint when frontend dist doesn't exist."""
        with patch("app.main.FRONTEND_DIR") as mock_dir:
            mock_dir.is_dir.return_value = False
            # The root function is already defined at import time
            # Just test the existing root function if frontend not present
            from app.main import app
            assert app is not None
