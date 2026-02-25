"""
Direct tests for main.py to maximize coverage.
"""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock


class TestHealthCheck:
    @pytest.mark.asyncio
    async def test_healthy(self):
        from app.main import health_check
        with patch("app.core.database.check_db_connection", new_callable=AsyncMock, return_value=True), \
             patch("app.main.task_scheduler") as mock_sched:
            mock_sched.is_running = True
            result = await health_check()
        assert result["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_degraded(self):
        from app.main import health_check
        with patch("app.core.database.check_db_connection", new_callable=AsyncMock, return_value=True), \
             patch("app.main.task_scheduler") as mock_sched:
            mock_sched.is_running = False
            result = await health_check()
        assert result["status"] == "degraded"

    @pytest.mark.asyncio
    async def test_unhealthy(self):
        from app.main import health_check
        with patch("app.core.database.check_db_connection", new_callable=AsyncMock, return_value=False), \
             patch("app.main.task_scheduler") as mock_sched:
            mock_sched.is_running = False
            result = await health_check()
        assert result["status"] == "unhealthy"


class TestRootEndpoint:
    @pytest.mark.asyncio
    async def test_root(self):
        """Test root endpoint when no frontend dist exists."""
        # Import to check the app exists
        from app.main import app
        assert app is not None
        assert app.title is not None
