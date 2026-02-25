"""
Pytest configuration and fixtures.

Provides shared test fixtures for all test modules.
"""

import asyncio
import os
from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.database import Base, get_db, get_data_db
from app.main import app

# Set testing environment variable to disable rate limiting
os.environ["TESTING"] = "true"


# Test database URL
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session", autouse=True)
def event_loop_policy() -> asyncio.AbstractEventLoopPolicy:
    """Set event loop policy for the entire test session."""
    policy = asyncio.DefaultEventLoopPolicy()
    asyncio.set_event_loop_policy(policy)
    yield policy
    # Clean up
    asyncio.set_event_loop_policy(None)


@pytest_asyncio.fixture(scope="function")
async def test_engine():
    """Create test database engine."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def test_db(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create test database session."""
    async_session_maker = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session_maker() as session:
        yield session


@pytest_asyncio.fixture(scope="function")
async def test_client(test_db):
    """Create test client with database override."""

    async def override_get_db():
        yield test_db

    async def override_get_data_db():
        yield test_db

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_data_db] = override_get_data_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()


def _clear_blacklist(bl):
    """Clear token blacklist regardless of backend type."""
    if hasattr(bl, '_blacklist'):
        # In-memory backend
        bl._blacklist.clear()
    elif hasattr(bl, '_redis'):
        # Redis backend – delete only our namespaced keys
        import itertools
        cursor, keys = bl._redis.scan(match=f"{bl._KEY_PREFIX}*", count=1000)
        all_keys = list(keys)
        while cursor:
            cursor, keys = bl._redis.scan(cursor=cursor, match=f"{bl._KEY_PREFIX}*", count=1000)
            all_keys.extend(keys)
        if all_keys:
            bl._redis.delete(*all_keys)


@pytest.fixture(autouse=True)
def _clear_test_state():
    """Clear shared state before each test."""
    from app.core.token_blacklist import token_blacklist
    from app.utils.cache import api_cache
    _clear_blacklist(token_blacklist)
    api_cache.clear()
    yield
    _clear_blacklist(token_blacklist)
    api_cache.clear()


@pytest.fixture
def test_user_data():
    """Provide test user data."""
    return {
        "email": "testuser@example.com",
        "password": "Password123!",
        "password_confirm": "Password123!",
    }


@pytest.fixture
def test_admin_data():
    """Provide test admin data."""
    return {
        "email": "admin@example.com",
        "password": "AdminPass123!",
        "password_confirm": "AdminPass123!",
    }


@pytest_asyncio.fixture
async def test_user(test_client, test_user_data):
    """Create a test user and return auth token."""
    # Register user
    await test_client.post("/api/auth/register", json=test_user_data)

    # Login to get token
    response = await test_client.post("/api/auth/login", json={
        "email": test_user_data["email"],
        "password": test_user_data["password"],
    })

    data = response.json()
    return data["data"]["access_token"]


@pytest_asyncio.fixture
async def test_user_token(test_client):
    """Create a test user and return auth token."""
    user_data = {
        "email": "testuser@example.com",
        "password": "Password123!",
        "password_confirm": "Password123!",
    }
    # Register user
    await test_client.post("/api/auth/register", json=user_data)

    # Login to get token
    response = await test_client.post("/api/auth/login", json={
        "email": user_data["email"],
        "password": user_data["password"],
    })

    data = response.json()
    return data["data"]["access_token"]


@pytest_asyncio.fixture
async def test_admin(test_client, test_admin_data, test_db):
    """Create a test admin user and return auth token."""
    from app.models.user import User, UserRole
    from app.core.security import hash_password

    # Create admin directly
    admin = User(
        username="testadmin",
        email=test_admin_data["email"],
        hashed_password=hash_password(test_admin_data["password"]),
        role=UserRole.ADMIN,
        is_active=True,
    )
    test_db.add(admin)
    await test_db.commit()

    # Login to get token
    response = await test_client.post("/api/auth/login", json={
        "email": test_admin_data["email"],
        "password": test_admin_data["password"],
    })

    data = response.json()
    return data["data"]["access_token"]


@pytest_asyncio.fixture
async def test_admin_token(test_client, test_db):
    """Create a test admin user and return auth token."""
    from app.models.user import User, UserRole
    from app.core.security import hash_password

    admin_email = "testadmin@example.com"
    admin_password = "AdminPass123!"

    # Create admin directly
    admin = User(
        username="testadmin",
        email=admin_email,
        hashed_password=hash_password(admin_password),
        role=UserRole.ADMIN,
        is_active=True,
    )
    test_db.add(admin)
    await test_db.commit()

    # Login to get token
    response = await test_client.post("/api/auth/login", json={
        "email": admin_email,
        "password": admin_password,
    })

    data = response.json()
    return data["data"]["access_token"]


def get_auth_headers(token: str) -> dict:
    """Helper to get auth headers."""
    return {"Authorization": f"Bearer {token}"}
