"""
Direct tests for tables API endpoints to maximize coverage.
"""

import pytest
from datetime import datetime, UTC
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.models.user import User, UserRole
from app.models.data_table import DataTable
from app.core.security import hash_password


async def _user(db):
    u = User(username="tu", email="tu@t.com", hashed_password=hash_password("P!1"), role=UserRole.USER, is_active=True)
    db.add(u)
    await db.commit()
    await db.refresh(u)
    return u


async def _table(db, name="test_tbl", row_count=100):
    t = DataTable(id=abs(hash(name)) % 100000, table_name=name, table_comment=f"Comment {name}", category="stock", row_count=row_count)
    db.add(t)
    await db.commit()
    await db.refresh(t)
    return t


class TestSafeTableName:
    def test_valid_name(self):
        from app.api.tables import _safe_table_name
        assert _safe_table_name("my_table") == "`my_table`"

    def test_invalid_name(self):
        from app.api.tables import _safe_table_name
        with pytest.raises(ValueError):
            _safe_table_name("drop table;--")

    def test_name_starts_with_number(self):
        from app.api.tables import _safe_table_name
        with pytest.raises(ValueError):
            _safe_table_name("1bad")


class TestListTablesDirect:
    @pytest.mark.asyncio
    async def test_list_all(self, test_db):
        from app.api.tables import list_tables
        from app.api.schemas import PaginatedParams
        user = await _user(test_db)
        await _table(test_db, "tbl_a")
        await _table(test_db, "tbl_b")
        params = PaginatedParams(page=1, page_size=20)
        result = await list_tables(search=None, params=params, db=test_db, current_user=user)
        assert result.data["total"] >= 2

    @pytest.mark.asyncio
    async def test_list_search(self, test_db):
        from app.api.tables import list_tables
        from app.api.schemas import PaginatedParams
        user = await _user(test_db)
        await _table(test_db, "unique_search_tbl")
        params = PaginatedParams(page=1, page_size=20)
        result = await list_tables(search="unique_search", params=params, db=test_db, current_user=user)
        assert result.data["total"] >= 1

    @pytest.mark.asyncio
    async def test_list_empty(self, test_db):
        from app.api.tables import list_tables
        from app.api.schemas import PaginatedParams
        user = await _user(test_db)
        params = PaginatedParams(page=1, page_size=20)
        result = await list_tables(search=None, params=params, db=test_db, current_user=user)
        assert result.success is True


class TestGetTableDirect:
    @pytest.mark.asyncio
    async def test_get(self, test_db):
        from app.api.tables import get_table
        user = await _user(test_db)
        tbl = await _table(test_db, "get_tbl")
        result = await get_table(table_id=tbl.id, db=test_db, current_user=user)
        assert result.data["table_name"] == "get_tbl"

    @pytest.mark.asyncio
    async def test_not_found(self, test_db):
        from app.api.tables import get_table
        user = await _user(test_db)
        with pytest.raises(HTTPException) as exc:
            await get_table(table_id=99999, db=test_db, current_user=user)
        assert exc.value.status_code == 404


class TestGetSchemaDirect:
    @pytest.mark.asyncio
    async def test_schema_table_not_found(self, test_db):
        from app.api.tables import get_table_schema
        user = await _user(test_db)
        with pytest.raises(HTTPException) as exc:
            await get_table_schema(table_id=99999, db=test_db, data_db=test_db, current_user=user)
        assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_schema_describe_fails(self, test_db):
        from app.api.tables import get_table_schema
        user = await _user(test_db)
        tbl = await _table(test_db, "schema_tbl")
        # DESCRIBE doesn't work on SQLite, so it will hit the except branch
        result = await get_table_schema(table_id=tbl.id, db=test_db, data_db=test_db, current_user=user)
        assert result.table_name == "schema_tbl"
        assert result.columns == []  # fallback to empty


class TestGetDataDirect:
    @pytest.mark.asyncio
    async def test_data_not_found(self, test_db):
        from app.api.tables import get_table_data
        user = await _user(test_db)
        with pytest.raises(HTTPException) as exc:
            await get_table_data(table_id=99999, page=1, page_size=10, db=test_db, data_db=test_db, current_user=user)
        assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_data_real_table(self, test_db):
        from app.api.tables import get_table_data
        user = await _user(test_db)
        # Create actual SQLite table in test_db (used as data_db too)
        await test_db.execute(text("CREATE TABLE IF NOT EXISTS real_data_tbl (id INTEGER PRIMARY KEY, val TEXT)"))
        await test_db.execute(text("INSERT INTO real_data_tbl (id, val) VALUES (1, 'hello')"))
        await test_db.execute(text("INSERT INTO real_data_tbl (id, val) VALUES (2, 'world')"))
        await test_db.commit()
        tbl = await _table(test_db, "real_data_tbl")
        result = await get_table_data(table_id=tbl.id, page=1, page_size=10, db=test_db, data_db=test_db, current_user=user)
        assert result["row_count"] == 2
        assert result["columns"] == ["id", "val"]

    @pytest.mark.asyncio
    async def test_data_nonexistent_table(self, test_db):
        from app.api.tables import get_table_data
        user = await _user(test_db)
        tbl = await _table(test_db, "nonexistent_sql_tbl")
        with pytest.raises(HTTPException) as exc:
            await get_table_data(table_id=tbl.id, page=1, page_size=10, db=test_db, data_db=test_db, current_user=user)
        assert exc.value.status_code == 500


class TestDeleteTableDirect:
    @pytest.mark.asyncio
    async def test_delete_not_found(self, test_db):
        from app.api.tables import delete_table
        user = await _user(test_db)
        with pytest.raises(HTTPException) as exc:
            await delete_table(table_id=99999, db=test_db, data_db=test_db, current_user=user)
        assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_success(self, test_db):
        from app.api.tables import delete_table
        user = await _user(test_db)
        await test_db.execute(text("CREATE TABLE IF NOT EXISTS del_tbl (id INTEGER)"))
        await test_db.commit()
        tbl = await _table(test_db, "del_tbl")
        result = await delete_table(table_id=tbl.id, db=test_db, data_db=test_db, current_user=user)
        assert result.success is True


class TestRefreshMetadataDirect:
    @pytest.mark.asyncio
    async def test_refresh_empty(self, test_db):
        from app.api.tables import refresh_table_metadata
        user = await _user(test_db)
        result = await refresh_table_metadata(db=test_db, data_db=test_db, current_user=user)
        assert result.success is True

    @pytest.mark.asyncio
    async def test_refresh_with_tables(self, test_db):
        from app.api.tables import refresh_table_metadata
        user = await _user(test_db)
        await test_db.execute(text("CREATE TABLE IF NOT EXISTS refresh_tbl (id INTEGER)"))
        await test_db.execute(text("INSERT INTO refresh_tbl (id) VALUES (1)"))
        await test_db.commit()
        await _table(test_db, "refresh_tbl", row_count=0)
        result = await refresh_table_metadata(db=test_db, data_db=test_db, current_user=user)
        assert result.success is True
        assert "Refreshed" in result.message

    @pytest.mark.asyncio
    async def test_refresh_nonexistent_table(self, test_db):
        from app.api.tables import refresh_table_metadata
        user = await _user(test_db)
        await _table(test_db, "ghost_tbl")
        # ghost_tbl doesn't exist in SQLite, should be skipped gracefully
        result = await refresh_table_metadata(db=test_db, data_db=test_db, current_user=user)
        assert result.success is True
