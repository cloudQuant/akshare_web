# 代码质量指南

本文档说明项目的代码质量工具、配置和最佳实践。

## 最近优化 (2025-03)

### 本轮优化（Services/Core/Utils 类型注解）

- **核心模块 `__init__` 返回类型**：`app/core/token_blacklist.py` 的 `_InMemoryBlacklist`、`_RedisBlacklist` 补充 `-> None`
- **服务层类型注解**：
  - `app/services/data_acquisition.py`、`data_service.py`、`execution_service.py`、`retry_service.py`、`scheduler.py`、`scheduler_service.py`、`script_service.py`：`__init__` 与公开/私有方法补充返回类型
  - `scheduler_service.py`：`start`、`shutdown`、`_initialize_scheduler`、`_build_trigger`、`_job_executed_listener`、`get_job` 等补充注解；`add_job`、`update_script` 的 `**kwargs: Any` 注解
- **data_fetch 模块**：
  - `akshare_provider.py`：`_get_connection_pool`、`FuncThread`、`AkshareProvider` 的 `__init__`、`connect_db`、`disconnect_db`、`_parse_db_url`、`fetch_ak_data` 等补充注解
  - `stock_zh_a_hist.py`：`StockZhAHistEm` 的 `__init__`、`fetch_data`、`main` 补充类型
- **工具模块**：`app/utils/cache.py` 的 `TTLCache.__init__` 与 `get`/`set`；`db_result`、`helpers`、`serialization` 中需 `Any` 的参数加 `noqa: ANN401`
- **Ruff per-file-ignores**：`app/data_fetch/providers/akshare_provider.py`、`app/data_fetch/scripts/*`、`app/services/scheduler_service.py` 对 `ANN401` 豁免（akshare 动态调用、APScheduler Job、通用缓存等场景需 `Any`）
- **收益**：`ruff check app/ --select ANN --ignore ANN001` 可通过；提升类型安全与可维护性

### 此前优化（API 返回类型注解）

- **API 层返回类型注解**：为 `app/api/` 下所有路由和辅助函数补充显式返回类型：
  - `auth.py`: register, login, refresh_token, logout, get_current_user_info → APIResponse
  - `data.py`: trigger_download → DataDownloadResponse, get_download_progress → DownloadProgressResponse, get_download_result → APIResponse, _bg_download → None
  - `interfaces.py`: list_categories, list_interfaces, get_interface, create_interface, update_interface, delete_interface → APIResponse
  - `users.py`: list_users → PaginatedResponse, get_user, update_user → UserResponse, delete_user, reset_user_password → APIResponse
  - `tables.py`: list_tables, get_table, delete_table, refresh_table_metadata → APIResponse; get_table_schema → TableSchemaResponse; get_table_data → APIResponse; export_table_data → StreamingResponse
  - `metrics.py`: prometheus_metrics → Response
- **收益**：提升类型安全、IDE 补全与文档；为未来启用 Ruff ANN 规则做铺垫

### 此前优化

- **前端覆盖率**：Vitest 阈值从 30% 提升至 40%（lines/functions/branches/statements）
- **E2E CI**：`.github/workflows/ci.yml` 新增 `e2e` job，启动后端 + 前端后运行 Playwright
- **type: ignore 清理**：`retry.py` 抽取 `_resolve_logger`、`_resolve_entrypoint`，移除多处 ignore；`rate_limit.py` 保留 slowapi 内部 API 的 1 处 arg-type ignore
- **高复杂度重构**：移除 5 处 `noqa: C901`，拆分为小函数：
  - `update_task` → `_apply_task_update`
  - `export_table_data` → `_stream_xlsx_export`、`_csv_export_stream`
  - `update_execution` → `_apply_execution_updates`
  - `execute_script` → `_resolve_entrypoint`
  - `save_data` → `_normalize_dataframe_columns`、`_align_df_to_table`、`_build_insert_sql`

### 首轮优化

- **Ruff C901 复杂度限制**：启用 `max-complexity=10`；`validate_schedule_expression` 拆分为 `_validate_daily/weekly/monthly/cron`
- **Import 排序**：修复 `app/cli.py`、`app/main.py` 中延迟导入的 import 块排序（I001）
- **Mypy 严格模式扩展**：`app.utils.db_result` 启用 `disallow_untyped_defs`
- **quality-full 增强**：`make quality-full` 新增 `typecheck`、`test`、`frontend-test`

### 历史优化

- **Mypy 严格模式**：`app.core.config`、`app.utils.constants`、`app.utils.validators` 启用 `disallow_untyped_defs`
- **前端覆盖率**：Vitest 配置 `thresholds`（lines/functions/branches/statements ≥30%）
- **Dependabot**：`.github/dependabot.yml` 每周扫描 pip、npm、github-actions
- **减少 type: ignore**：新增 `app.utils.db_result.get_rowcount()` 和 `_get_pool_stats()` 统一处理
- **前端 ESLint + Prettier**：`eslint.config.js` 引入 `@vue/eslint-config-prettier/skip-formatting`，避免规则冲突
- **前端覆盖率统一**：Vitest `branches` 阈值从 20% 提升至 30%，与 lines/functions/statements 一致
- **db_result 扩展**：新增 `get_columns_from_result()`，`app.api.tables` 移除 3 处 `type: ignore[attr-defined]`
- **Pre-commit pip-audit**：依赖变更时（requirements.txt/pyproject.toml）自动运行 pip-audit

## 工具栈

| 层级 | 工具 | 用途 |
|------|------|------|
| 后端 | Ruff | Lint + 格式化 |
| 后端 | Bandit | 安全扫描 |
| 后端 | Mypy | 类型检查 |
| 后端 | pytest + pytest-cov | 测试与覆盖率（≥70%） |
| 前端 | ESLint + TypeScript | Lint + 类型 |
| 前端 | Prettier | 格式化 |
| 前端 | Vitest | 单元测试 |
| 通用 | pre-commit | 提交前钩子 |

## 配置文件

- `.editorconfig` - 编辑器统一格式（缩进、换行、编码）
- `bandit.yaml` - Bandit 排除与跳过规则
- `pyproject.toml` - Ruff、Mypy、pytest、coverage 配置
- `frontend/eslint.config.js` - ESLint flat config

## Ruff 规则

- **E, F** - 错误与 Pyflakes
- **I, UP** - import 排序与 pyupgrade
- **B** - 防 bug（如函数默认参数）
- **N, W** - 命名与警告
- **SIM** - 简化写法
- **S** - 安全
- **PTH** - pathlib
- **R** - 可维护性
- **TCH** - 类型检查相关
- **ERA** - 注释掉的代码检测
- **C901** - 圈复杂度限制（max-complexity=10），超限处使用 `# noqa: C901` 暂豁免

## 可选严格检查

逐步启用更严格规则时可参考：

```bash
# API 层已补充返回类型，可验证 app/api 无 ANN 遗漏
ruff check app/api/ --select ANN --ignore ANN001

# Ruff 文档字符串（DOC）与注解（ANN）- 其他模块需逐步修复
ruff check app/ --select DOC,ANN --ignore ANN001
```

**注意**：ANN 规则（如 ANN201/ANN202）会要求所有公开/私有函数添加返回类型注解。`app/api/` 已全部补充；`app/services/`、`app/core/` 等可后续分模块启用。

## 类型标注

- `app/py.typed` - PEP 561 标记，表明包支持类型
- 已启用 `disallow_untyped_defs` 的模块：`app.models.*`、`app.api.schemas`、`app.core.config`、`app.utils.constants`、`app.utils.validators`、`app.utils.db_result`
- `type: ignore` 仅用于 SQLAlchemy/第三方库等无法标注处

## 提交前检查

```bash
pip install pre-commit
pre-commit install
# 之后每次 git commit 自动运行
pre-commit run --all-files  # 手动全量运行
```
