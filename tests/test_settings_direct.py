"""
Direct tests for settings API endpoints to maximize coverage.
"""

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserRole
from app.core.security import hash_password


async def _admin(db):
    u = User(username="sadm", email="sadm@t.com", hashed_password=hash_password("P!1"), role=UserRole.ADMIN, is_active=True)
    db.add(u)
    await db.commit()
    await db.refresh(u)
    return u


class TestGetDatabaseConfigDirect:
    @pytest.mark.asyncio
    async def test_get_config(self, test_db):
        from app.api.settings import get_database_config
        admin = await _admin(test_db)
        result = await get_database_config(current_admin=admin)
        assert result.is_warehouse is False
        assert result.host is not None


class TestGetWarehouseConfigDirect:
    @pytest.mark.asyncio
    async def test_get_warehouse(self, test_db):
        from app.api.settings import get_warehouse_config
        admin = await _admin(test_db)
        result = await get_warehouse_config(current_admin=admin)
        assert result.is_warehouse is True


class TestTestConnectionDirect:
    @pytest.mark.asyncio
    async def test_connection_failure(self, test_db):
        from app.api.settings import test_database_connection, TestConnectionRequest
        admin = await _admin(test_db)
        req = TestConnectionRequest(host="invalid_host", port=3306, database="test", user="test", password="test")
        result = await test_database_connection(request=req, current_admin=admin, db=test_db)
        assert result.success is False
        assert "失败" in result.message


class TestUpdateConfigDirect:
    @pytest.mark.asyncio
    async def test_update_not_implemented(self, test_db):
        from app.api.settings import update_database_config, DatabaseConfigRequest
        admin = await _admin(test_db)
        req = DatabaseConfigRequest(host="localhost", port=3306, database="test", user="root", password="pass")
        with pytest.raises(HTTPException) as exc:
            await update_database_config(request=req, current_admin=admin)
        assert exc.value.status_code == 501


class TestWarehouseTestConnectionDirect:
    @pytest.mark.asyncio
    async def test_warehouse_connection(self, test_db):
        from app.api.settings import test_warehouse_connection, TestConnectionRequest
        admin = await _admin(test_db)
        req = TestConnectionRequest(host="invalid_host", port=3306, database="test", user="test", password="test")
        result = await test_warehouse_connection(request=req, current_admin=admin)
        assert result.success is False
