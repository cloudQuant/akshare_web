"""
Data acquisition service.

Handles execution of akshare data interface calls and database storage.
"""

import asyncio
from datetime import UTC, datetime
from typing import Any

import akshare as ak
import pandas as pd
from loguru import logger
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.interface import DataInterface
from app.models.data_table import DataTable
from app.models.task import TaskExecution, TaskStatus
from app.utils.helpers import generate_table_name, clean_column_names, safe_table_name


class DataAcquisitionService:
    """
    Service for acquiring financial data using akshare.

    Handles data retrieval, validation, and storage with progress tracking.
    """

    def __init__(self):
        self._active_executions: dict[int, dict] = {}

    async def execute_download(
        self,
        execution_id: int,
        interface_id: int,
        parameters: dict[str, Any],
        db: AsyncSession,
    ) -> int | None:
        """
        Execute data download for an interface.

        Args:
            execution_id: Task execution record ID
            interface_id: Data interface to execute
            parameters: Parameters for the interface
            db: Database session

        Returns:
            Number of rows affected or None if failed

        Raises:
            Exception: If data acquisition fails
        """
        from sqlalchemy import select

        # Get interface
        result = await db.execute(
            select(DataInterface).where(DataInterface.id == interface_id)
        )
        interface = result.scalar_one_or_none()

        if interface is None:
            raise ValueError(f"Interface {interface_id} not found")

        # Get execution record
        exec_result = await db.execute(
            select(TaskExecution).where(TaskExecution.id == execution_id)
        )
        execution = exec_result.scalar_one_or_none()

        if execution is None:
            raise ValueError(f"Execution {execution_id} not found")

        # Track active execution
        self._active_executions[execution_id] = {
            "interface_id": interface_id,
            "parameters": parameters,
            "started_at": datetime.now(UTC),
        }

        try:
            # Execute akshare function
            logger.info(
                f"Executing interface {interface.name} with parameters: {parameters}"
            )

            # Call akshare function
            data = await self._call_akshare_function(interface, parameters)

            if data is None or (isinstance(data, pd.DataFrame) and data.empty):
                logger.warning(f"Interface {interface.name} returned no data")
                execution.status = TaskStatus.COMPLETED
                execution.completed_at = datetime.now(UTC)
                execution.rows_affected = 0
                await db.commit()
                return 0

            # Store data in database
            rows_affected = await self._store_data(
                data=data,
                interface=interface,
                execution_id=execution_id,
                db=db,
            )

            return rows_affected

        except Exception as e:
            logger.error(f"Data acquisition failed for {interface.name}: {e}")
            execution.status = TaskStatus.FAILED
            execution.error_message = str(e)
            execution.completed_at = datetime.now(UTC)
            await db.commit()
            raise

        finally:
            # Cleanup tracking
            self._active_executions.pop(execution_id, None)

    async def _call_akshare_function(
        self,
        interface: DataInterface,
        parameters: dict[str, Any],
    ) -> pd.DataFrame | None:
        """
        Call akshare function with parameters.

        Args:
            interface: Data interface definition
            parameters: Function parameters

        Returns:
            DataFrame with data or None
        """
        try:
            # Get the akshare module function
            func = getattr(ak, interface.name, None)

            if func is None:
                raise AttributeError(f"akshare function {interface.name} not found")

            # Build arguments
            kwargs = {}
            for param_name, param_value in parameters.items():
                # Skip None values
                if param_value is not None:
                    kwargs[param_name] = param_value

            # Call function (run in thread pool for blocking calls)
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(
                None,
                lambda: func(**kwargs) if kwargs else func()
            )

            # Ensure result is DataFrame
            if not isinstance(result, pd.DataFrame):
                logger.warning(f"Interface {interface.name} did not return DataFrame")
                return None

            return result

        except AttributeError:
            logger.error(f"Function {interface.name} not found in akshare")
            raise
        except Exception as e:
            logger.error(f"Error calling akshare function {interface.name}: {e}")
            raise

    async def _store_data(
        self,
        data: pd.DataFrame,
        interface: DataInterface,
        execution_id: int,
        db: AsyncSession,
    ) -> int:
        """
        Store data in database.

        Creates table if needed and inserts data.

        Args:
            data: DataFrame to store
            interface: Source interface
            execution_id: Associated execution record
            db: Database session

        Returns:
            Number of rows inserted
        """
        # Generate table name from interface name
        table_name = self._generate_table_name(interface.name)

        # Clean column names
        data.columns = self._clean_column_names(data.columns)

        # Create table if not exists
        await self._create_table_if_not_exists(
            table_name=table_name,
            data=data,
            db=db,
        )

        # Insert data
        rows_affected = await self._insert_data(
            table_name=table_name,
            data=data,
            db=db,
        )

        # Update or create data table metadata
        await self._update_table_metadata(
            table_name=table_name,
            interface_id=interface.id,
            execution_id=execution_id,
            row_count=rows_affected,
            db=db,
        )

        return rows_affected

    def _generate_table_name(self, interface_name: str) -> str:
        """Generate SQL table name from interface name."""
        return generate_table_name(interface_name)

    def _clean_column_names(self, columns) -> list[str]:
        """Clean DataFrame column names for SQL."""
        return clean_column_names(columns)

    async def _create_table_if_not_exists(
        self,
        table_name: str,
        data: pd.DataFrame,
        db: AsyncSession,
    ) -> None:
        """Create table if it doesn't exist."""
        # Build CREATE TABLE statement
        columns_defs = []
        for col in data.columns:
            dtype = data[col].dtype
            if pd.api.types.is_integer_dtype(dtype):
                sql_type = "BIGINT"
            elif pd.api.types.is_float_dtype(dtype):
                sql_type = "DOUBLE"
            elif pd.api.types.is_datetime64_any_dtype(dtype):
                sql_type = "DATETIME"
            else:
                # String type with length
                max_len = data[col].astype(str).str.len().max()
                max_len = min(max(max_len or 1, 50), 500)
                sql_type = f"VARCHAR({max_len})"

            columns_defs.append(f"`{col}` {sql_type}")

        # Add ID and timestamp columns
        all_columns = ["id BIGINT AUTO_INCREMENT PRIMARY KEY"] + columns_defs + [
            "created_at DATETIME DEFAULT CURRENT_TIMESTAMP"
        ]

        quoted_name = safe_table_name(table_name)
        create_sql = f"""
            CREATE TABLE IF NOT EXISTS {quoted_name} (
                {', '.join(all_columns)},
                INDEX idx_created_at (created_at)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """

        await db.execute(text(create_sql))
        await db.commit()

    async def _insert_data(
        self,
        table_name: str,
        data: pd.DataFrame,
        db: AsyncSession,
    ) -> int:
        """Insert data into table."""
        if data.empty:
            return 0

        # Prepare data for insertion
        records = data.to_dict("records")

        # Build INSERT statement
        columns = list(data.columns)
        columns_str = ", ".join([f"`{col}`" for col in columns])
        placeholders = ", ".join([f":{col}" for col in columns])

        quoted_name = safe_table_name(table_name)
        insert_sql = f"""
            INSERT INTO {quoted_name} ({columns_str})
            VALUES ({placeholders})
        """

        # Insert in batches using executemany for better performance
        batch_size = 2000
        rows_inserted = 0

        for i in range(0, len(records), batch_size):
            batch = records[i : i + batch_size]
            await db.execute(text(insert_sql), batch)
            rows_inserted += len(batch)
            # Flush periodically to avoid large transaction memory
            if rows_inserted % 10000 == 0:
                await db.flush()

        await db.commit()
        logger.info(f"Inserted {rows_inserted} rows into {table_name}")
        return rows_inserted

    async def _update_table_metadata(
        self,
        table_name: str,
        interface_id: int,
        execution_id: int,
        row_count: int,
        db: AsyncSession,
    ) -> None:
        """Update data table metadata record."""
        from sqlalchemy import select

        # Get existing metadata
        result = await db.execute(
            select(DataTable).where(DataTable.table_name == table_name)
        )
        table_meta = result.scalar_one_or_none()

        # Get current total row count
        quoted_name = safe_table_name(table_name)
        count_result = await db.execute(
            text(f"SELECT COUNT(*) FROM {quoted_name}")
        )
        total_rows = count_result.scalar() or 0

        if table_meta:
            # Update existing
            table_meta.row_count = total_rows
            table_meta.last_update_time = datetime.now(UTC)
            table_meta.last_update_status = "success"
        else:
            # Create new
            table_meta = DataTable(
                table_name=table_name,
                table_comment=table_name.replace("ak_", "").replace("_", " ").title(),
                row_count=total_rows,
                last_update_time=datetime.now(UTC),
                last_update_status="success",
            )
            db.add(table_meta)

        await db.commit()

    def get_progress(self, execution_id: int) -> dict[str, Any]:
        """
        Get progress of an active execution.

        Args:
            execution_id: Execution record ID

        Returns:
            Progress information dict
        """
        if execution_id not in self._active_executions:
            return {
                "execution_id": execution_id,
                "status": "not_found",
                "progress": 0,
            }

        info = self._active_executions[execution_id]
        return {
            "execution_id": execution_id,
            "status": "running",
            "interface_id": info.get("interface_id"),
            "started_at": info.get("started_at"),
        }

    def cancel_execution(self, execution_id: int) -> bool:
        """
        Cancel an active execution.

        Args:
            execution_id: Execution record ID

        Returns:
            True if cancelled, False otherwise
        """
        if execution_id in self._active_executions:
            self._active_executions.pop(execution_id, None)
            return True
        return False


# Note: asyncio import moved to top of file
