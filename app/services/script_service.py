"""Script service for managing data acquisition scripts"""

import asyncio
import importlib
import json
import os
import re
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.data_fetch.configs import SCRIPT_CATEGORIES
from app.data_fetch.providers.akshare_provider import AkshareProvider
from app.models.data_script import DataScript, ScriptFrequency

from loguru import logger


class ScriptService:
    """脚本管理服务"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.script_base_path = "app/data_fetch/scripts"

    async def get_scripts(
        self,
        category: str | None = None,
        frequency: ScriptFrequency | None = None,
        is_active: bool | None = None,
        keyword: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[list[DataScript], int]:
        """
        获取脚本列表

        Args:
            category: 分类筛选
            frequency: 频率筛选
            is_active: 状态筛选
            keyword: 关键词搜索
            skip: 跳过数量
            limit: 返回数量

        Returns:
            (脚本列表, 总数)
        """
        query = select(DataScript)

        # 筛选条件
        if category:
            query = query.where(DataScript.category == category)
        if frequency:
            query = query.where(DataScript.frequency == frequency)
        if is_active is not None:
            query = query.where(DataScript.is_active == is_active)
        if keyword:
            filters = [
                DataScript.script_name.contains(keyword),
                DataScript.script_id.contains(keyword),
                DataScript.description.contains(keyword),
            ]
            keyword_filter = filters[0]
            for f in filters[1:]:
                keyword_filter = keyword_filter | f
            query = query.where(keyword_filter)

        # 获取总数
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        # 分页查询
        query = query.offset(skip).limit(limit).order_by(
            DataScript.category, DataScript.script_id
        )
        result = await self.db.execute(query)
        scripts = result.scalars().all()

        return list(scripts), total

    async def get_script(self, script_id: str) -> DataScript | None:
        """获取脚本详情"""
        result = await self.db.execute(
            select(DataScript).where(DataScript.script_id == script_id)
        )
        return result.scalar_one_or_none()

    async def create_script(
        self,
        script_id: str,
        script_name: str,
        category: str,
        module_path: str,
        **kwargs,
    ) -> DataScript:
        """创建脚本"""
        script = DataScript(
            script_id=script_id,
            script_name=script_name,
            category=category,
            module_path=module_path,
            **kwargs,
        )
        self.db.add(script)
        await self.db.commit()
        await self.db.refresh(script)
        return script

    async def update_script(
        self, script_id: str, **kwargs
    ) -> DataScript | None:
        """更新脚本"""
        script = await self.get_script(script_id)
        if not script:
            return None

        for key, value in kwargs.items():
            if hasattr(script, key):
                setattr(script, key, value)

        script.updated_at = datetime.now(UTC)
        await self.db.commit()
        await self.db.refresh(script)
        return script

    async def delete_script(self, script_id: str) -> bool:
        """删除脚本"""
        script = await self.get_script(script_id)
        if not script:
            return False

        await self.db.delete(script)
        await self.db.commit()
        return True

    async def toggle_script(self, script_id: str, active: bool | None = None) -> bool:
        """
        切换脚本激活状态

        Args:
            script_id: 脚本ID
            active: 目标状态，如果为None则切换当前状态

        Returns:
            是否切换成功
        """
        script = await self.get_script(script_id)
        if not script:
            return False

        if active is None:
            script.is_active = not script.is_active
        else:
            script.is_active = active

        await self.db.commit()
        return True

    async def execute_script(
        self,
        script_id: str,
        execution_id: str,
        params: dict[str, Any] | None = None,
        timeout: int | None = None,
    ) -> dict[str, Any]:
        """
        执行脚本

        Args:
            script_id: 脚本ID
            execution_id: 执行ID
            params: 执行参数
            timeout: 超时时间（秒）

        Returns:
            执行结果
        """
        script = await self.get_script(script_id)
        if not script:
            raise ValueError(f"Script not found: {script_id}")

        if not script.is_active:
            raise ValueError(f"Script is not active: {script_id}")

        # 动态导入模块
        if not script.module_path:
            raise ValueError(f"Script has no module_path: {script_id}")

        try:
            module = importlib.import_module(script.module_path)

            # 查找类或函数
            func_name = script.function_name or "main"
            entrypoint = getattr(module, func_name, None)

            # 如果没有函数，查找类
            if not callable(entrypoint):
                for obj in module.__dict__.values():
                    if isinstance(obj, type) and obj.__module__ == module.__name__:
                        # 检查是否有fetch_data或run方法
                        if hasattr(obj, "fetch_data") or hasattr(obj, "run"):
                            entrypoint = obj()
                            func_name = "fetch_data" if hasattr(entrypoint, "fetch_data") else "run"
                            break

                if not entrypoint or not callable(getattr(entrypoint, func_name, None)):
                    raise AttributeError(
                        f"No callable entrypoint found for module={script.module_path}"
                    )

            # 执行函数
            func = getattr(entrypoint, func_name, None) if not callable(entrypoint) else entrypoint

            if asyncio.iscoroutinefunction(func):
                coro = func(**(params or {}))
            else:
                # 在线程中执行同步函数
                coro = asyncio.to_thread(func, **(params or {}))

            # Apply timeout if specified
            if timeout and timeout > 0:
                try:
                    result = await asyncio.wait_for(coro, timeout=timeout)
                except asyncio.TimeoutError:
                    raise TimeoutError(
                        f"Script {script_id} execution timed out after {timeout}s"
                    )
            else:
                result = await coro

            return {
                "success": True,
                "script_id": script_id,
                "execution_id": execution_id,
                "result": self._serialize_result(result),
                "error": None,
            }

        except Exception as e:
            logger.error(f"Script execution failed: {script_id}, error: {str(e)}")
            return {
                "success": False,
                "script_id": script_id,
                "execution_id": execution_id,
                "result": None,
                "error": str(e),
            }

    def _serialize_result(self, result: Any) -> Any:
        """序列化执行结果"""
        import pandas as pd

        if isinstance(result, pd.DataFrame):
            return {
                "type": "DataFrame",
                "rows": len(result),
                "columns": list(result.columns),
                "data": result.to_dict(orient="records")[:100],  # 只返回前100行
            }
        elif hasattr(result, "__dict__"):
            return str(result)
        return result

    async def get_categories(self) -> list[str]:
        """获取所有脚本分类"""
        result = await self.db.execute(
            select(DataScript.category).distinct()
        )
        return [row[0] for row in result.all()]

    async def scan_and_register_scripts(self) -> dict[str, Any]:
        """
        扫描并注册所有脚本

        Returns:
            注册结果统计
        """
        registered_count = 0
        updated_count = 0
        errors = []

        script_base_path = os.path.join("app", "data_fetch", "scripts")

        for category, config in SCRIPT_CATEGORIES.items():
            category_path = os.path.join(script_base_path, category)
            if not await asyncio.to_thread(os.path.exists, category_path):
                continue

            for sub_category in config.get("sub_categories", []):
                sub_path = os.path.join(category_path, sub_category)
                if not await asyncio.to_thread(os.path.exists, sub_path):
                    continue

                filenames = await asyncio.to_thread(os.listdir, sub_path)
                for filename in filenames:
                    if not filename.endswith(".py") or filename.startswith("__"):
                        continue

                    try:
                        file_path = os.path.join(sub_path, filename)
                        result = await self._register_script_from_file(
                            file_path, script_base_path
                        )
                        if result == "created":
                            registered_count += 1
                        elif result == "updated":
                            updated_count += 1
                    except Exception as e:
                        errors.append(f"{filename}: {str(e)}")

        return {
            "registered_count": registered_count,
            "updated_count": updated_count,
            "errors": errors,
        }

    async def _register_script_from_file(
        self, file_path: str, base_path: str
    ) -> str:
        """
        从文件注册脚本

        Returns:
            'created', 'updated', or 'skipped'
        """
        filename = os.path.basename(file_path)
        rel_path = os.path.relpath(file_path, base_path)
        module_path = "app.data_fetch.scripts." + rel_path.replace(".py", "").replace(os.sep, ".")

        # 解析脚本信息
        rel_parts = rel_path.split(os.sep)
        category = rel_parts[0] if len(rel_parts) >= 1 else "common"
        sub_category = rel_parts[1] if len(rel_parts) >= 2 else None

        # 判断频率
        parent_dir = os.path.basename(os.path.dirname(file_path))
        frequency_map = {
            "hourly": ScriptFrequency.HOURLY,
            "daily": ScriptFrequency.DAILY,
            "weekly": ScriptFrequency.WEEKLY,
            "monthly": ScriptFrequency.MONTHLY,
        }
        frequency = frequency_map.get(parent_dir, ScriptFrequency.DAILY)

        script_id = filename.replace(".py", "")
        target_table = self._extract_target_table(file_path)

        # 检查是否已存在
        existing = await self.get_script(script_id)

        if existing:
            # 检查是否需要更新
            needs_update = any([
                existing.module_path != module_path,
                existing.category != category,
                not existing.target_table and bool(target_table),
            ])
            if needs_update:
                await self.update_script(
                    script_id,
                    module_path=module_path,
                    category=category,
                    sub_category=sub_category,
                    frequency=frequency,
                    target_table=target_table,
                )
                return "updated"
            return "skipped"

        # 创建新脚本
        await self.create_script(
            script_id=script_id,
            script_name=script_id.replace("_", " ").title(),
            category=category,
            sub_category=sub_category,
            frequency=frequency,
            module_path=module_path,
            target_table=target_table,
            is_active=True,
        )
        return "created"

    def _extract_target_table(self, file_path: str) -> str | None:
        """从脚本文件中提取目标表名"""
        try:
            with open(file_path, encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except Exception:
            return None

        m = re.search(r"""self\.table_name\s*=\s*["']([A-Za-z0-9_]+)["']""", content)
        if m:
            return m.group(1)
        return None

    async def get_script_stats(self) -> dict[str, Any]:
        """获取脚本统计信息"""
        total_query = select(func.count(DataScript.id))
        active_query = select(func.count(DataScript.id)).where(DataScript.is_active.is_(True))

        total_result = await self.db.execute(total_query)
        active_result = await self.db.execute(active_query)

        total = total_result.scalar() or 0
        active = active_result.scalar() or 0

        # 按分类统计
        category_query = select(
            DataScript.category, func.count(DataScript.id)
        ).group_by(DataScript.category)
        category_result = await self.db.execute(category_query)
        by_category = {row[0]: row[1] for row in category_result.all()}

        # 按频率统计
        frequency_query = select(
            DataScript.frequency, func.count(DataScript.id)
        ).group_by(DataScript.frequency)
        frequency_result = await self.db.execute(frequency_query)
        by_frequency = {row[0].value: row[1] for row in frequency_result.all()}

        return {
            "total": total,
            "active": active,
            "inactive": total - active,
            "by_category": by_category,
            "by_frequency": by_frequency,
        }
