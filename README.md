# akshare_web

A web-based financial data management platform for [akshare](https://github.com/akfamily/akshare).

## 项目说明

本项目包含三个部分：

1. **akshare** - 金融数据接口库（可通过 `pip install -U .` 安装）
2. **akshare_web** - Web管理平台后端（FastAPI）
3. **frontend** - Web管理平台前端（Vue3 + TypeScript + Element Plus）

## 安装 akshare

```bash
cd /path/to/akshare_web
pip install -U .
```

安装后可以直接使用 akshare：

```python
import akshare as ak

# 获取股票数据
df = ak.stock_zh_a_hist(symbol="000001", period="daily", start_date="20240101", adjust="qfq")

# 获取基金数据
df = ak.fund_etf_spot_em()

# 获取宏观经济数据
df = ak.macro_china_gdp()
```

## 启动 akshare_web Web 平台

```bash
cd /path/to/akshare_web
./start_app.sh
```

启动脚本会自动：
1. 安装 akshare 包
2. 安装 web 平台依赖
3. 初始化数据库
4. 启动 FastAPI 服务

访问：
- API 文档: http://localhost:8000/docs
- 健康检查: http://localhost:8000/health

## 功能特性

### akshare (1,069+ 接口)
- **股票**: 395 个接口
- **宏观**: 226 个接口
- **指数**: 79 个接口
- **基金**: 68 个接口
- **期货**: 59 个接口
- **期权**: 46 个接口
- **债券**: 39 个接口
- 其他: 共 46 个类别

### akshare_web (Web 平台)
- 数据脚本管理
  - 自动扫描和注册数据获取脚本
  - 按分类组织（stocks/funds/futures/indexs/options/bonds等）
  - 支持多种执行频率（hourly/daily/weekly/monthly）
  - 自定义脚本支持（管理员可创建/编辑/删除）
- 定时任务配置
  - 支持 Cron 表达式
  - 支持 Interval 间隔执行
  - 任务启用/暂停/删除
  - 自动重试机制（指数退避）
- 执行记录追踪
  - 详细执行状态（pending/running/completed/failed/timeout）
  - 执行前后数据行数统计
  - 错误信息和堆栈记录
  - 重试次数和耗时统计
  - 执行统计和趋势分析
- 用户权限管理
  - 管理员/普通用户角色
  - 基于角色的访问控制
  - JWT 认证机制
- 数据库配置
  - 主数据库配置管理
  - 数据仓库配置管理
  - 连接测试功能
- 数据表管理
  - 数据表浏览
  - 表结构查看
  - 数据预览
- Web 界面
  - Vue3 + Element Plus
  - 响应式设计
  - 暗色/亮色主题切换
- RESTful API
  - 完整的 CRUD 操作
  - 分页查询支持
  - 批量操作支持
  - API 速率限制

## 项目结构

```
akshare_web/
├── akshare/                      # akshare 数据接口库
│   ├── stock/                    # 股票数据接口
│   ├── fund/                     # 基金数据接口
│   ├── futures/                  # 期货数据接口
│   ├── macro/                    # 宏观数据接口
│   └── ...                       # 其他类别
├── app/                          # akshare_web Web 平台
│   ├── api/                      # API 路由
│   │   ├── auth.py               # 认证相关
│   │   ├── tasks.py              # 定时任务管理
│   │   ├── scripts.py            # 数据脚本管理
│   │   ├── executions.py         # 执行记录查询
│   │   └── ...
│   ├── core/                     # 核心功能
│   │   ├── config.py             # 配置管理
│   │   ├── database.py           # 数据库连接
│   │   └── security.py           # 安全认证
│   ├── data_fetch/               # 数据获取模块
│   │   ├── scripts/              # 数据脚本目录
│   │   │   ├── stocks/           # 股票脚本
│   │   │   ├── funds/            # 基金脚本
│   │   │   ├── futures/          # 期货脚本
│   │   │   └── ...
│   │   ├── providers/            # 数据提供者
│   │   │   └── akshare_provider.py
│   │   └── configs/              # 配置
│   ├── models/                   # 数据模型
│   │   ├── user.py               # 用户模型
│   │   ├── data_script.py        # 脚本模型
│   │   └── task.py               # 任务模型
│   ├── services/                 # 业务逻辑
│   │   ├── scheduler.py          # 任务调度器
│   │   ├── scheduler_service.py  # 调度服务
│   │   ├── execution_service.py  # 执行服务
│   │   └── script_service.py     # 脚本服务
│   └── main.py                   # 应用入口
├── frontend/                     # Vue3 前端
│   ├── src/
│   │   ├── api/                  # API 客户端
│   │   ├── components/           # 组件
│   │   ├── stores/               # Pinia 状态管理
│   │   ├── views/                # 页面视图
│   │   └── router/               # 路由配置
│   ├── package.json
│   └── vite.config.ts
├── alembic/                      # 数据库迁移
├── docker-compose.yml            # Docker 编排
├── Dockerfile                    # Docker 镜像
├── nginx.conf                    # Nginx 配置
├── akshare_web.service           # systemd 服务
├── start_app.sh                  # 启动脚本
├── DEPLOYMENT.md                 # 部署文档
└── requirements.txt              # 依赖列表
```

## API 使用示例

```bash
# 注册用户
curl -X POST "http://localhost:8000/api/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","email":"test@example.com","password":"password123"}'

# 登录
curl -X POST "http://localhost:8000/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"password123"}'

# 获取数据脚本列表
curl -X GET "http://localhost:8000/api/scripts?page=1&page_size=20" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"

# 扫描并注册新脚本（管理员）
curl -X POST "http://localhost:8000/api/scripts/scan" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"

# 创建定时任务
curl -X POST "http://localhost:8000/api/tasks" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"每日A股数据","script_id":"stock_zh_a_hist","schedule_type":"daily","schedule_expression":"15:00"}'

# 获取执行记录
curl -X GET "http://localhost:8000/api/executions?page=1&page_size=20" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"

# 手动触发任务执行
curl -X POST "http://localhost:8000/api/tasks/1/trigger" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

## 默认账户

- 用户名: `admin`
- 密码: `admin123`

## 编写数据脚本

数据脚本位于 `app/data_fetch/scripts/` 目录下，按分类和频率组织：

```
app/data_fetch/scripts/
├── stocks/
│   ├── daily/
│   │   └── stock_zh_a_hist.py
│   └── weekly/
├── funds/
│   └── daily/
└── ...
```

示例脚本模板：

```python
from app.data_fetch.providers.akshare_provider import AkshareProvider

class MyDataScript(AkshareProvider):
    def __init__(self, db_url=None, logger=None):
        super().__init__(db_url, logger)
        self.table_name = "my_data_table"
        self.create_table_sql = """
        CREATE TABLE IF NOT EXISTS `my_data_table` (
            `R_ID` INT AUTO_INCREMENT PRIMARY KEY,
            `column1` VARCHAR(100),
            `column2` DECIMAL(10, 2),
            `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """

    def fetch_data(self, **kwargs):
        # 获取数据
        df = self.fetch_ak_data("ak_function_name", **kwargs)
        if df is not None and not df.empty:
            self.create_table_if_not_exists(self.table_name, self.create_table_sql)
            self.save_data(df, self.table_name, ignore_duplicates=True)
        return df
```

## 前端访问

Vue3 前端已开发完成，包含以下功能：
- 用户登录/注册界面
- 数据接口浏览和搜索
- 定时任务管理界面
- 执行记录查询和统计
- 数据表管理界面
- 系统设置（管理员）

启动后端服务后，访问前端：

```bash
cd frontend
npm install
npm run dev
```

访问: http://localhost:5173

## 生产部署

详细的部署文档请参考 [DEPLOYMENT.md](./DEPLOYMENT.md)。

### Docker 部署（推荐）

```bash
# 构建并启动所有服务
docker-compose up -d

# 查看状态
docker-compose ps

# 查看日志
docker-compose logs -f
```

### systemd 服务部署

```bash
# 安装服务
sudo cp akshare_web.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable akshare_web
sudo systemctl start akshare_web
```

### 环境配置

复制生产环境配置模板：

```bash
cp .env.production .env
nano .env  # 修改数据库、密钥等配置
```

## 许可证

MIT License
