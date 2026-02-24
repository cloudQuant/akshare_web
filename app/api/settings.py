"""
Database settings API endpoints.

Provides endpoints for managing database connection configurations.
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, validator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.core.database import get_db
from app.core.config import settings
from app.api.dependencies import get_current_admin_user
from app.models.user import User

router = APIRouter()


class DatabaseConfigResponse(BaseModel):
    """Database configuration response (without password)."""

    host: str
    port: int
    database: str
    user: str
    is_warehouse: bool = False


class DatabaseConfigRequest(BaseModel):
    """Database configuration update request."""

    host: str = Field(..., min_length=1, max_length=255)
    port: int = Field(..., ge=1, le=65535)
    database: str = Field(..., min_length=1, max_length=100)
    user: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=1, max_length=255)
    is_warehouse: bool = False


class TestConnectionRequest(BaseModel):
    """Database connection test request."""

    host: str = Field(..., min_length=1, max_length=255)
    port: int = Field(..., ge=1, le=65535)
    database: str = Field(..., min_length=1, max_length=100)
    user: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=1, max_length=255)


class TestConnectionResponse(BaseModel):
    """Database connection test response."""

    success: bool
    message: str


@router.get("/database", )
async def get_database_config(
    current_admin: User = Depends(get_current_admin_user),
) -> DatabaseConfigResponse:
    """
    Get current database configuration (without password).

    Requires admin privileges.
    """
    return DatabaseConfigResponse(
        host=settings.mysql_host,
        port=settings.mysql_port,
        database=settings.mysql_database,
        user=settings.mysql_user,
        is_warehouse=False,
    )


@router.get("/database/warehouse", )
async def get_warehouse_config(
    current_admin: User = Depends(get_current_admin_user),
) -> DatabaseConfigResponse:
    """
    Get data warehouse database configuration (without password).

    Requires admin privileges.
    """
    return DatabaseConfigResponse(
        host=settings.data_mysql_host or settings.mysql_host,
        port=settings.data_mysql_port or settings.mysql_port,
        database=settings.data_mysql_database or settings.mysql_database,
        user=settings.data_mysql_user or settings.mysql_user,
        is_warehouse=True,
    )


@router.post("/database/test", )
async def test_database_connection(
    request: TestConnectionRequest,
    current_admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
) -> TestConnectionResponse:
    """
    Test database connection with provided credentials.

    Requires admin privileges.
    """
    try:
        # Create a connection URL with the provided credentials
        import aiomysql

        connection_url = (
            f"mysql://{request.user}:{request.password}@"
            f"{request.host}:{request.port}/{request.database}"
        )

        # Try to establish a connection
        conn = await aiomysql.connect(
            host=request.host,
            port=request.port,
            user=request.user,
            password=request.password,
            db=request.database,
            connect_timeout=5,
        )

        # Execute a simple test query
        async with conn.cursor() as cursor:
            await cursor.execute("SELECT 1")
            result = await cursor.fetchone()

        await conn.close()

        if result and result[0] == 1:
            return TestConnectionResponse(
                success=True,
                message="数据库连接成功",
            )
        else:
            return TestConnectionResponse(
                success=False,
                message="数据库连接异常",
            )

    except ImportError:
        # aiomysql not available, try with SQLAlchemy
        try:
            from sqlalchemy import create_engine
            from sqlalchemy.pool import QueuePool

            engine = create_engine(
                f"mysql+pymysql://{request.user}:{request.password}@"
                f"{request.host}:{request.port}/{request.database}",
                poolclass=QueuePool,
                pool_size=1,
                max_overflow=0,
            )

            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))

            return TestConnectionResponse(
                success=True,
                message="数据库连接成功",
            )

        except Exception as e:
            return TestConnectionResponse(
                success=False,
                message=f"数据库连接失败: {str(e)}",
            )

    except Exception as e:
        return TestConnectionResponse(
            success=False,
            message=f"数据库连接失败: {str(e)}",
        )


@router.put("/database", )
async def update_database_config(
    request: DatabaseConfigRequest,
    current_admin: User = Depends(get_current_admin_user),
) -> DatabaseConfigResponse:
    """
    Update database configuration.

    Note: This will update environment variables and requires service restart.

    Requires admin privileges.
    """
    # In production, this would update a configuration file or environment
    # For now, we'll return a message indicating manual update is needed

    # TODO: Implement configuration persistence
    # Options:
    # 1. Update .env file (requires file system access)
    # 2. Store in database settings table
    # 3. Use a configuration service (Consul, etcd, etc.)

    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="配置更新功能暂未实现。请手动更新 .env 文件并重启服务。",
    )


@router.post("/database/warehouse/test", )
async def test_warehouse_connection(
    request: TestConnectionRequest,
    current_admin: User = Depends(get_current_admin_user),
) -> TestConnectionResponse:
    """
    Test data warehouse database connection with provided credentials.

    Requires admin privileges.
    """
    # Same implementation as test_database_connection
    return await test_database_connection(request, current_admin, None)
