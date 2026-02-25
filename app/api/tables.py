"""
Data table API routes.

Provides endpoints for managing data tables created by data acquisition.
"""

from typing import Any

import re

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, get_current_admin_user, get_db
from app.core.database import get_data_db
from app.api.schemas import (
    APIResponse,
    PaginatedParams,
    PaginatedResponse,
    TableResponse,
    TableSchemaResponse,
)
from app.models.data_table import DataTable
from app.utils.helpers import safe_table_name as _safe_table_name


router = APIRouter()


@router.get("/", )
async def list_tables(
    search: str | None = Query(None, description="Search in table name, display name, or description"),
    params: PaginatedParams = Depends(),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """
    List data tables.

    Returns paginated list of data tables with metadata.
    """
    # Build query
    query = select(DataTable)

    if search:
        search_pattern = f"%{search}%"
        query = query.where(
            (DataTable.table_name.ilike(search_pattern))
            | (DataTable.table_comment.ilike(search_pattern))
        )

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Get paginated results
    query = (
        query.order_by(DataTable.updated_at.desc())
        .offset((params.page - 1) * params.page_size)
        .limit(params.page_size)
    )

    result = await db.execute(query)
    tables = result.scalars().all()

    items = [
        TableResponse.model_validate(table)
        for table in tables
    ]

    return APIResponse(
        success=True,
        message="success",
        data={
            "items": [item.model_dump(mode="json") for item in items],
            "total": total,
            "page": params.page,
            "page_size": params.page_size,
            "total_pages": (total + params.page_size - 1) // params.page_size,
        }
    )


@router.get("/{table_id}", )
async def get_table(
    table_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """
    Get data table details.

    Returns detailed information about a specific data table.
    """
    result = await db.execute(
        select(DataTable).where(DataTable.id == table_id)
    )
    table = result.scalar_one_or_none()

    if table is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data table not found",
        )

    return APIResponse(
        success=True,
        message="success",
        data=TableResponse.model_validate(table).model_dump(mode="json"),
    )


@router.get("/{table_id}/schema", )
async def get_table_schema(
    table_id: int,
    db: AsyncSession = Depends(get_db),
    data_db: AsyncSession = Depends(get_data_db),
    current_user = Depends(get_current_user),
):
    """
    Get data table schema.

    Returns the database schema for a specific table including
    column names, types, and constraints.
    """
    result = await db.execute(
        select(DataTable).where(DataTable.id == table_id)
    )
    table = result.scalar_one_or_none()

    if table is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data table not found",
        )

    # Get actual schema from data warehouse
    try:
        query = text(f"DESCRIBE {_safe_table_name(table.table_name)}")
        schema_result = await data_db.execute(query)
        columns = [
            {
                "name": row[0],
                "type": row[1],
                "nullable": row[2] == "YES",
                "key": row[3] if row[3] else None,
                "default": row[4],
            }
            for row in schema_result.fetchall()
        ]
    except Exception:
        # If table doesn't exist or query fails, return empty
        columns = []

    return TableSchemaResponse(
        table_name=table.table_name,
        columns=columns,
        row_count=table.row_count,
        last_update_time=table.last_update_time,
    )


@router.get("/{table_id}/data")
async def get_table_data(
    table_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    data_db: AsyncSession = Depends(get_data_db),
    current_user = Depends(get_current_user),
):
    """
    Get data from table.

    Returns actual data rows from the specified table.
    """
    result = await db.execute(
        select(DataTable).where(DataTable.id == table_id)
    )
    table = result.scalar_one_or_none()

    if table is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data table not found",
        )

    offset = (page - 1) * page_size
    limit = page_size

    # Query actual data from data warehouse
    try:
        query = text(f"SELECT * FROM {_safe_table_name(table.table_name)} ORDER BY id LIMIT :limit OFFSET :offset")
        data_result = await data_db.execute(query, {"limit": limit, "offset": offset})

        # Get column names from cursor description
        columns = list(data_result.keys()) if data_result.returns_rows else []
        rows = data_result.fetchall()

        # Convert rows to dicts, handling non-serializable types
        import decimal
        from datetime import date, datetime
        def serialize_value(v: Any) -> Any:
            if isinstance(v, decimal.Decimal):
                return float(v)
            if isinstance(v, (date, datetime)):
                return v.isoformat()
            if isinstance(v, bytes):
                return v.decode("utf-8", errors="replace")
            return v

        serialized_rows = [
            {col: serialize_value(row[i]) for i, col in enumerate(columns)}
            for row in rows
        ]

        return APIResponse(
            success=True,
            message="success",
            data={
                "table_name": table.table_name,
                "columns": columns,
                "rows": serialized_rows,
                "row_count": len(rows),
                "offset": offset,
                "limit": limit,
            },
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to query table data: {str(e)}",
        )


@router.delete("/{table_id}", )
async def delete_table(
    table_id: int,
    db: AsyncSession = Depends(get_db),
    data_db: AsyncSession = Depends(get_data_db),
    current_user = Depends(get_current_admin_user),
):
    """
    Delete data table.

    Admin only endpoint for dropping tables and metadata.
    """
    result = await db.execute(
        select(DataTable).where(DataTable.id == table_id)
    )
    table = result.scalar_one_or_none()

    if table is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data table not found",
        )

    # Drop the actual table from data warehouse
    try:
        query = text(f"DROP TABLE IF EXISTS {_safe_table_name(table.table_name)}")
        await data_db.execute(query)
        await data_db.commit()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to drop table: {str(e)}",
        )

    # Delete metadata
    await db.delete(table)
    await db.commit()

    return APIResponse(
        success=True,
        message=f"Table {table.table_name} deleted successfully",
    )


@router.get("/{table_id}/export")
async def export_table_data(
    table_id: int,
    format: str = Query("csv", pattern="^(csv|xlsx)$", description="Export format: csv or xlsx"),
    limit: int = Query(100000, ge=1, le=1000000, description="Maximum rows to export"),
    db: AsyncSession = Depends(get_db),
    data_db: AsyncSession = Depends(get_data_db),
    current_user = Depends(get_current_user),
):
    """
    Export table data as CSV or Excel file.

    CSV uses streaming to keep memory bounded for large tables.
    Excel is limited to 50,000 rows due to in-memory requirement.
    """
    import csv
    import io
    from fastapi.responses import StreamingResponse

    result = await db.execute(
        select(DataTable).where(DataTable.id == table_id)
    )
    table = result.scalar_one_or_none()

    if table is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data table not found",
        )

    safe_name = re.sub(r'[^\w]', '_', table.table_name)
    xlsx_limit = min(limit, 50000)

    if format == "xlsx":
        # Excel requires full load; cap at 50k rows
        try:
            query = text(
                f"SELECT * FROM {_safe_table_name(table.table_name)} LIMIT :limit"
            )
            data_result = await data_db.execute(query, {"limit": xlsx_limit})
            columns = list(data_result.keys()) if data_result.returns_rows else []
            rows = data_result.fetchall()
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to query table data: {str(e)}",
            )

        import pandas as pd
        df = pd.DataFrame(rows, columns=columns)
        buf = io.BytesIO()
        df.to_excel(buf, index=False, engine="openpyxl")
        buf.seek(0)
        return StreamingResponse(
            buf,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="{safe_name}.xlsx"'},
        )
    else:
        # CSV: stream in batches to keep memory low
        batch_size = 10000

        async def _csv_stream():
            import decimal
            from datetime import date, datetime as _dt

            def _serialise(v):
                if isinstance(v, decimal.Decimal):
                    return str(v)
                if isinstance(v, (date, _dt)):
                    return v.isoformat()
                if isinstance(v, bytes):
                    return v.decode("utf-8", errors="replace")
                return v

            offset = 0
            header_written = False
            while offset < limit:
                batch_limit = min(batch_size, limit - offset)
                query = text(
                    f"SELECT * FROM {_safe_table_name(table.table_name)} "
                    f"LIMIT :limit OFFSET :offset"
                )
                data_result = await data_db.execute(
                    query, {"limit": batch_limit, "offset": offset}
                )
                columns = list(data_result.keys()) if data_result.returns_rows else []
                rows = data_result.fetchall()

                if not rows:
                    if not header_written and columns:
                        buf = io.StringIO()
                        writer = csv.writer(buf)
                        writer.writerow(columns)
                        yield buf.getvalue()
                    break

                buf = io.StringIO()
                writer = csv.writer(buf)
                if not header_written:
                    writer.writerow(columns)
                    header_written = True
                for row in rows:
                    writer.writerow([_serialise(v) for v in row])
                yield buf.getvalue()

                offset += len(rows)
                if len(rows) < batch_limit:
                    break

        return StreamingResponse(
            _csv_stream(),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{safe_name}.csv"'},
        )


@router.post("/refresh", )
async def refresh_table_metadata(
    db: AsyncSession = Depends(get_db),
    data_db: AsyncSession = Depends(get_data_db),
    current_user = Depends(get_current_admin_user),
):
    """
    Refresh table metadata.

    Admin only endpoint to update row counts and schema info
    from actual database tables.
    """
    # Get all tables
    result = await db.execute(select(DataTable))
    tables = result.scalars().all()

    updated_count = 0

    for table in tables:
        try:
            # Get row count from data warehouse
            count_query = text(f"SELECT COUNT(*) FROM {_safe_table_name(table.table_name)}")
            count_result = await data_db.execute(count_query)
            table.row_count = count_result.scalar() or 0

            updated_count += 1
        except Exception:
            # Skip tables that don't exist in warehouse
            pass

    await db.commit()

    return APIResponse(
        success=True,
        message=f"Refreshed metadata for {updated_count} tables",
    )
