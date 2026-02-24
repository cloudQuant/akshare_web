"""
Authentication API routes.

Provides endpoints for user registration, login, token refresh, and logout.
"""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import CurrentUser, get_db
from app.api.schemas import (
    APIResponse,
    LoginRequest,
    RegisterRequest,
    RefreshTokenRequest,
)
from app.api.rate_limit import rate_limit
from app.core.security import (
    verify_password,
    hash_password,
    create_access_token,
    create_refresh_token,
)
from app.models.user import User, UserRole

router = APIRouter()


@router.post("/register", response_model=APIResponse, status_code=status.HTTP_201_CREATED)
@rate_limit("5/minute")  # Limit registration attempts
async def register(
    request: RegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Register a new user account.

    Creates a new user with regular user role.
    """
    # Normalize email to lowercase
    email = request.email.lower()

    # Validate password confirmation
    if request.password != request.password_confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Passwords do not match",
        )

    # Check if email already exists
    result = await db.execute(select(User).where(User.email == email))
    if result.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Generate username from email (part before @)
    base_username = email.split("@")[0][:46]  # Max length 50, leave room for counter
    username = base_username
    # Ensure username is unique by appending number if needed
    counter = 1
    max_attempts = 1000  # Prevent infinite loop

    while counter <= max_attempts:
        result = await db.execute(select(User).where(User.username == username))
        if result.scalar_one_or_none() is None:
            break
        username = f"{base_username}{counter}"
        counter += 1

    if counter > max_attempts:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to generate unique username. Please contact support.",
        )

    # Create new user
    user = User(
        username=username,
        email=email,  # Use normalized email
        hashed_password=hash_password(request.password),
        role=UserRole.USER,
        is_active=True,
    )

    db.add(user)
    await db.commit()
    await db.refresh(user)

    # Create tokens
    access_token = create_access_token(data={"sub": str(user.id), "email": user.email})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})

    return APIResponse(
        success=True,
        message="注册成功",
        data={
            "user_id": user.id,
            "email": user.email,
            "access_token": access_token,
            "refresh_token": refresh_token,
        },
    )


@router.post("/login", response_model=APIResponse)
@rate_limit("10/minute")  # Limit login attempts
async def login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Authenticate user and return access token.

    Validates credentials and returns JWT access token for authentication.
    """
    # Normalize email
    email = request.email.lower()

    # Find user by email
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    # Verify password
    if user is None or not verify_password(request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="邮箱或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled",
        )

    # Update last login
    user.last_login = datetime.now(UTC)
    await db.commit()

    # Create tokens
    access_token = create_access_token(data={"sub": str(user.id), "email": user.email})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})

    return APIResponse(
        success=True,
        message="登录成功",
        data={
            "access_token": access_token,
            "refresh_token": refresh_token,
            "user": {
                "user_id": user.id,
                "email": user.email,
                "role": user.role.value,
                "created_at": user.created_at.isoformat(),
                "updated_at": user.updated_at.isoformat() if user.updated_at else None,
            },
        },
    )


@router.post("/refresh", response_model=APIResponse)
async def refresh_token(
    request: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Refresh access token using refresh token.

    Validates refresh token and returns new access token.
    """
    from app.core.security import verify_token

    payload = verify_token(request.refresh_token, token_type="refresh")

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    user_id = payload.get("sub")
    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()

    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    # Create new access token
    access_token = create_access_token(data={"sub": str(user.id), "email": user.email})
    new_refresh_token = create_refresh_token(data={"sub": str(user.id)})

    return APIResponse(
        success=True,
        message="Token refreshed",
        data={
            "access_token": access_token,
            "refresh_token": new_refresh_token,
        },
    )


@router.post("/logout", response_model=APIResponse)
async def logout():
    """
    Logout current user.

    In a production environment, this would invalidate the token
    in a Redis store or similar. For now, it's a client-side operation.
    """
    return APIResponse(
        success=True,
        message="Logout successful",
    )


@router.get("/me", response_model=APIResponse)
async def get_current_user_info(
    current_user: CurrentUser,
):
    """
    Get current user information.

    Returns the authenticated user's profile information.
    """
    return APIResponse(
        success=True,
        data={
            "user_id": current_user.id,
            "email": current_user.email,
            "role": current_user.role.value,
            "is_active": current_user.is_active,
            "created_at": current_user.created_at.isoformat(),
            "updated_at": current_user.updated_at.isoformat() if current_user.updated_at else None,
        },
    )
