"""
Task models for scheduled data acquisition.

Defines models for scheduled tasks and their execution records.
"""

import enum
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import BigInteger, Boolean, DateTime, Enum, ForeignKey, Integer, JSON, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class TaskStatus(str, enum.Enum):
    """Task execution status enumeration."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


class ScheduleType(str, enum.Enum):
    """Schedule type enumeration."""

    ONCE = "once"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    CRON = "cron"
    INTERVAL = "interval"


class TriggeredBy(str, enum.Enum):
    """Execution trigger type enumeration."""

    SCHEDULER = "scheduler"
    MANUAL = "manual"
    API = "api"


class ScheduledTask(Base):
    """
    Scheduled task model for automated data acquisition.

    Attributes:
        id: Primary key
        name: Task name
        description: Task description
        user_id: Owner user ID
        script_id: Data script to execute
        schedule_type: Type of schedule
        schedule_expression: Schedule expression (cron or preset)
        parameters: Parameters to pass to script
        is_active: Whether task is enabled
        retry_on_failure: Whether to retry on failure
        max_retries: Maximum retry attempts
        timeout: Timeout in seconds (0 = use script default)
        last_execution_at: Last execution timestamp
        next_execution_at: Next scheduled execution
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """

    __tablename__ = "scheduled_tasks"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
    )
    script_id: Mapped[str] = mapped_column(
        String(100),
        ForeignKey("data_scripts.script_id"),
        nullable=False,
    )
    schedule_type: Mapped[ScheduleType] = mapped_column(
        Enum(ScheduleType),
        default=ScheduleType.DAILY,
        nullable=False,
    )
    schedule_expression: Mapped[str] = mapped_column(String(100), nullable=False)
    parameters: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    retry_on_failure: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    max_retries: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    timeout: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    last_execution_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    next_execution_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<ScheduledTask(id={self.id}, name={self.name}, active={self.is_active})>"


class TaskExecution(Base):
    """
    Task execution record model.

    Tracks individual task executions with detailed status and results.

    Attributes:
        id: Primary key
        execution_id: Unique execution identifier
        task_id: Parent task ID
        script_id: Script ID that was executed
        params: Parameters used for execution
        status: Execution status
        start_time: Execution start time
        end_time: Execution completion time
        duration: Execution duration in seconds
        result: Execution result data (JSON)
        error_message: Error message if failed
        error_trace: Full error traceback
        rows_before: Table row count before execution
        rows_after: Table row count after execution
        retry_count: Retry attempt number
        triggered_by: How the execution was triggered
        operator_id: User who triggered manual execution
        created_at: Record creation timestamp
        updated_at: Last update timestamp
    """

    __tablename__ = "task_executions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    execution_id: Mapped[str] = mapped_column(
        String(100), unique=True, index=True, nullable=False
    )
    task_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("scheduled_tasks.id"),
        nullable=False,
    )
    script_id: Mapped[str] = mapped_column(String(100), nullable=False)
    params: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    status: Mapped[TaskStatus] = mapped_column(
        Enum(TaskStatus),
        default=TaskStatus.PENDING,
        nullable=False,
        index=True,
    )
    start_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    end_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    duration: Mapped[float | None] = mapped_column(Numeric(precision=10, scale=2), nullable=True)
    result: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_trace: Mapped[str | None] = mapped_column(Text, nullable=True)
    rows_before: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rows_after: Mapped[int | None] = mapped_column(Integer, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    triggered_by: Mapped[TriggeredBy] = mapped_column(
        Enum(TriggeredBy),
        default=TriggeredBy.SCHEDULER,
        nullable=False,
    )
    operator_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("users.id"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<TaskExecution(id={self.id}, execution_id={self.execution_id}, status={self.status.value})>"
