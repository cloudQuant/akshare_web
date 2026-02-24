"""
Common API schemas and Pydantic models.

Defines request/response schemas used across API endpoints.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator
from app.models.user import UserRole


# Base response schema
class APIResponse(BaseModel):
    """Standard API response wrapper."""

    success: bool = True
    message: str | None = None
    data: Any | None = None


class ErrorResponse(BaseModel):
    """Error response schema."""

    success: bool = False
    message: str
    detail: str | None = None
    error_code: str | None = None


# Pagination schemas
class PaginatedParams(BaseModel):
    """Pagination parameters."""

    page: int = Field(default=1, ge=1, description="Page number")
    page_size: int = Field(default=20, ge=1, le=100, description="Items per page")


class PaginatedResponse(BaseModel):
    """Paginated response wrapper."""

    items: list[Any]
    total: int
    page: int
    page_size: int
    total_pages: int


# Authentication schemas
class LoginRequest(BaseModel):
    """Login request schema."""

    email: EmailStr
    password: str = Field(..., min_length=1)


class RegisterRequest(BaseModel):
    """Registration request schema."""

    email: EmailStr
    password: str = Field(
        ...,
        min_length=8,
        max_length=100,
        description="Password must be at least 8 characters with letters and digits"
    )
    password_confirm: str = Field(..., min_length=8, max_length=100)

    @field_validator('password')
    @classmethod
    def validate_password_complexity(cls, v: str) -> str:
        """Validate password has at least one letter and one digit."""
        if not any(c.isalpha() for c in v):
            raise ValueError('Password must contain at least one letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v


class TokenResponse(BaseModel):
    """Token response schema."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class RefreshTokenRequest(BaseModel):
    """Refresh token request schema."""

    refresh_token: str


# User schemas
class UserResponse(BaseModel):
    """User response schema."""

    id: int
    email: str
    role: str
    is_active: bool
    created_at: datetime
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class UserListResponse(BaseModel):
    """User list item schema."""

    user_id: int
    email: str
    role: str
    created_at: str


class UserUpdateRoleRequest(BaseModel):
    """User role update request schema."""

    role: str = Field(..., pattern="^(Admin|User)$")


class UserUpdateRequest(BaseModel):
    """User update request schema."""

    full_name: str | None = Field(None, max_length=100)
    email: EmailStr | None = None
    role: UserRole | None = None
    is_active: bool | None = None
    is_verified: bool | None = None


# Interface schemas
class CategoryResponse(BaseModel):
    """Interface category response schema."""

    id: int
    name: str
    description: str | None = None
    icon: str | None = None
    sort_order: int

    model_config = ConfigDict(from_attributes=True)


class InterfaceParameterSchema(BaseModel):
    """Interface parameter schema."""

    name: str
    display_name: str
    param_type: str
    description: str | None = None
    default_value: str | None = None
    required: bool = False
    options: list[str] | None = None


class InterfaceResponse(BaseModel):
    """Data interface response schema."""

    id: int
    name: str
    display_name: str
    description: str | None = None
    category_id: int
    category_name: str | None = None
    module_path: str | None = None
    function_name: str | None = None
    parameters: dict[str, Any]
    return_type: str
    example: str | None = None
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class InterfaceListResponse(BaseModel):
    """Interface list item schema."""

    id: int
    name: str
    display_name: str
    description: str | None = None
    category_name: str | None = None
    is_active: bool


# Task schemas
class TaskCreateRequest(BaseModel):
    """Task creation request schema."""

    interface_id: int
    name: str
    description: str | None = None
    schedule_type: str = Field(..., pattern="^(once|daily|weekly|monthly|cron)$")
    schedule_expression: str
    parameters: dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True
    retry_on_failure: bool = True
    max_retries: int = Field(default=3, ge=0, le=10)


class TaskUpdateRequest(BaseModel):
    """Task update request schema."""

    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = Field(None, max_length=500)
    schedule_type: str | None = Field(None, pattern="^(once|daily|weekly|monthly|cron)$")
    schedule_expression: str | None = None
    parameters: dict[str, Any] | None = None
    is_active: bool | None = None
    retry_on_failure: bool | None = None
    max_retries: int | None = Field(None, ge=0, le=10)


class TaskResponse(BaseModel):
    """Task response schema."""

    id: int
    name: str
    description: str | None
    user_id: int
    interface_id: int
    interface_name: str | None = None
    schedule_type: str
    schedule_expression: str
    parameters: dict[str, Any]
    is_active: bool
    retry_on_failure: bool
    max_retries: int
    last_execution_at: datetime | None
    next_execution_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TaskExecutionResponse(BaseModel):
    """Task execution response schema."""

    id: int
    task_id: int
    status: str
    started_at: datetime | None
    completed_at: datetime | None
    duration_ms: int | None
    rows_affected: int | None
    error_message: str | None
    retry_count: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Data acquisition schemas
class DataDownloadRequest(BaseModel):
    """Data download request schema."""

    interface_id: int
    parameters: dict[str, Any] = Field(default_factory=dict)


class DataDownloadResponse(BaseModel):
    """Data download response schema."""

    execution_id: int
    status: str
    message: str | None = None


class DownloadProgressResponse(BaseModel):
    """Download progress response schema."""

    execution_id: int
    status: str
    progress: float = Field(ge=0, le=100)
    message: str | None = None
    rows_processed: int | None = None
    started_at: datetime | None
    estimated_completion: datetime | None = None


# Data Table schemas
class TableResponse(BaseModel):
    """Data table response schema."""

    id: int
    table_name: str
    table_comment: str | None = None
    category: str | None = None
    script_id: str | None = None
    row_count: int = 0
    last_update_time: datetime | None = None
    last_update_status: str | None = None
    data_start_date: Any | None = None
    data_end_date: Any | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TableSchemaResponse(BaseModel):
    """Table schema response schema."""

    table_name: str
    columns: list[dict[str, Any]]
    row_count: int
    last_update_time: datetime | None = None


# Data Script schemas (for akshare integration)
class ParameterSchema(BaseModel):
    """Parameter definition schema."""

    name: str
    type: str
    required: bool
    default_value: Any | None = None
    description: str


class DataScriptResponse(BaseModel):
    """Data script response schema."""

    id: int
    name: str
    description: str
    category: str
    parameters: list[ParameterSchema]
    module_path: str
    function_name: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DataScriptListResponse(BaseModel):
    """Data script list item schema."""

    id: int
    name: str
    description: str
    category: str


# Schedule Template schemas
class ScheduleTemplate(BaseModel):
    """Schedule template schema."""

    value: str
    label: str
    description: str
    cron_expression: str


class ScheduleTemplatesResponse(BaseModel):
    """Schedule templates list response."""

    templates: list[ScheduleTemplate]
