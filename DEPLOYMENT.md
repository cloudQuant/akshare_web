# akshare_web 部署指南

本文档提供 akshare_web 平台的完整部署指南，包括生产环境配置、Docker 部署、系统服务配置等。

## 目录

- [系统要求](#系统要求)
- [环境准备](#环境准备)
- [配置说明](#配置说明)
- [部署方式](#部署方式)
  - [Docker 部署 (推荐)](#docker-部署-推荐)
  - [Systemd 服务部署](#systemd-服务部署)
  - [传统部署](#传统部署)
- [数据库配置](#数据库配置)
- [前端部署](#前端部署)
- [反向代理配置](#反向代理配置)
- [监控与日志](#监控与日志)
- [安全加固](#安全加固)
- [故障排查](#故障排查)

---

## 系统要求

### 最低配置

- **操作系统**: Linux (Ubuntu 20.04+, CentOS 7+, Debian 10+)
- **CPU**: 2 核
- **内存**: 4 GB RAM
- **磁盘**: 20 GB 可用空间
- **Python**: 3.11+
- **MySQL**: 8.0+

### 推荐配置

- **CPU**: 4+ 核
- **内存**: 8+ GB RAM
- **磁盘**: SSD 50+ GB
- **MySQL**: 独立服务器
- **Redis**: 用于缓存 (可选)

---

## 环境准备

### 1. 安装系统依赖

**Ubuntu/Debian:**

```bash
sudo apt-get update
sudo apt-get install -y \
    python3.11 \
    python3.11-venv \
    python3.11-dev \
    build-essential \
    default-libmysqlclient-dev \
    pkg-config \
    git \
    nginx \
    certbot
```

**CentOS/RHEL:**

```bash
sudo yum update -y
sudo yum install -y \
    python311 \
    python311-devel \
    gcc \
    gcc-c++ \
    mariadb-devel \
    git \
    nginx \
    certbot
```

### 2. 创建专用用户

```bash
# 创建运行用户
sudo useradd -m -s /bin/bash akshare
sudo passwd akshare
```

### 3. 克隆代码

```bash
sudo mkdir -p /opt
sudo chown akshare:akshare /opt
sudo -u akshare git clone <repository-url> /opt/akshare_web
cd /opt/akshare_web
```

---

## 配置说明

### 环境变量配置

创建 `.env` 文件：

```bash
cp .env.example .env
nano .env
```

**必填配置项:**

```bash
# 应用配置
ENVIRONMENT=production
SECRET_KEY=<生成一个强随机密钥>
ALLOWED_HOSTS=localhost, your-domain.com

# 数据库配置
DATABASE_URL=mysql+aiomysql://user:password@localhost:3306/akshare_web
WAREHOUSE_DB_URL=mysql+aiomysql://user:password@localhost:3307/akshare_warehouse

# JWT 配置
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=7

# 服务器配置
HOST=0.0.0.0
PORT=8000
WORKERS=4
```

**生成 SECRET_KEY:**

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

---

## 部署方式

### Docker 部署 (推荐)

#### 1. 安装 Docker

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
```

#### 2. 配置 docker-compose

```bash
cp .env.example .env
nano .env  # 修改配置
```

#### 3. 启动服务

```bash
# 构建并启动所有服务
docker-compose up -d

# 查看状态
docker-compose ps

# 查看日志
docker-compose logs -f

# 只启动后端
docker-compose up -d backend mysql

# 同时启动数据仓库
docker-compose --profile warehouse up -d
```

#### 4. 初始化数据库

```bash
# 进入容器
docker-compose exec backend bash

# 运行初始化
akshare-web init-db
akshare-web load-interfaces

# 退出容器
exit
```

#### 5. 停止服务

```bash
docker-compose down
# 保留数据卷
docker-compose down -v  # 删除数据卷（慎用）
```

---

### Systemd 服务部署

#### 1. 创建虚拟环境

```bash
cd /opt/akshare_web
python3.11 -m venv venv
source venv/bin/activate

# 安装依赖
pip install --upgrade pip
pip install -r requirements.txt

# 安装 akshare
pip install -e ./akshare
```

#### 2. 配置系统服务

```bash
# 复制服务文件
sudo cp akshare_web.service /etc/systemd/system/

# 修改路径（如需要）
sudo nano /etc/systemd/system/akshare_web.service

# 重载 systemd
sudo systemctl daemon-reload

# 启用开机自启
sudo systemctl enable akshare_web

# 启动服务
sudo systemctl start akshare_web

# 查看状态
sudo systemctl status akshare_web

# 查看日志
sudo journalctl -u akshare_web -f
```

#### 3. 初始化数据库

```bash
sudo -u akshare /opt/akshare_web/venv/bin/akshare-web init-db
sudo -u akshare /opt/akshare_web/venv/bin/akshare-web load-interfaces
```

---

### 传统部署

#### 1. 安装依赖

```bash
cd /opt/akshare_web
pip install -r requirements.txt
pip install -e ./akshare
```

#### 2. 初始化数据库

```bash
alembic upgrade head
akshare-web init-db
```

#### 3. 启动应用

**开发模式:**

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**生产模式:**

```bash
uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 4 \
    --loop uvloop
```

**使用 gunicorn:**

```bash
gunicorn app.main:app \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8000 \
    --timeout 120 \
    --access-logfile logs/access.log \
    --error-logfile logs/error.log
```

---

## 数据库配置

### MySQL 配置

#### 1. 安装 MySQL

```bash
sudo apt-get install -y mysql-server
sudo mysql_secure_installation
```

#### 2. 创建数据库和用户

```sql
CREATE DATABASE akshare_web CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'akshare_user'@'localhost' IDENTIFIED BY 'strong_password';
GRANT ALL PRIVILEGES ON akshare_web.* TO 'akshare_user'@'localhost';
FLUSH PRIVILEGES;

-- 创建数据仓库（可选）
CREATE DATABASE akshare_warehouse CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'warehouse_user'@'localhost' IDENTIFIED BY 'strong_password';
GRANT ALL PRIVILEGES ON akshare_warehouse.* TO 'warehouse_user'@'localhost';
FLUSH PRIVILEGES;
```

#### 3. 性能优化

编辑 `/etc/mysql/mysql.conf.d/mysqld.cnf`:

```ini
[mysqld]
# 连接配置
max_connections = 200
connect_timeout = 10

# InnoDB 配置
innodb_buffer_pool_size = 2G
innodb_log_file_size = 256M
innodb_flush_log_at_trx_commit = 2
innodb_flush_method = O_DIRECT

# 查询缓存
query_cache_size = 0  # MySQL 8.0 已移除

# 慢查询日志
slow_query_log = 1
slow_query_log_file = /var/log/mysql/slow.log
long_query_time = 2
```

#### 4. 备份策略

```bash
#!/bin/bash
# 备份脚本 /opt/backup/akshare_backup.sh

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/opt/backup"
DB_NAME="akshare_web"

# 全量备份
mysqldump -u root -p$MYSQL_ROOT_PASSWORD \
    --single-transaction \
    --routines \
    --triggers \
    --events \
    $DB_NAME > $BACKUP_DIR/akshare_$DATE.sql

# 压缩
gzip $BACKUP_DIR/akshare_$DATE.sql

# 删除 30 天前的备份
find $BACKUP_DIR -name "akshare_*.sql.gz" -mtime +30 -delete
```

设置定时任务:

```bash
crontab -e
# 每天凌晨 2 点备份
0 2 * * * /opt/backup/akshare_backup.sh
```

---

## 前端部署

### 1. 构建前端

```bash
cd frontend

# 安装依赖
npm install

# 生产构建
npm run build

# 构建结果在 dist/ 目录
```

### 2. 部署到 Nginx

```bash
# 复制构建文件
sudo cp -r dist/* /var/www/akshare_web/

# 配置 Nginx (见下节)
```

### 3. 环境配置

创建 `frontend/.env.production`:

```bash
VITE_API_BASE_URL=https://api.your-domain.com
VITE_WS_BASE_URL=wss://api.your-domain.com
VITE_APP_TITLE=akshare_web
```

---

## 反向代理配置

### Nginx 配置

#### 1. 基本配置

```nginx
server {
    listen 80;
    server_name your-domain.com;

    # 前端静态文件
    location / {
        root /var/www/akshare_web;
        try_files $uri $uri/ /index.html;
    }

    # API 代理
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # WebSocket (如果使用)
    location /ws/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

#### 2. 启用 HTTPS

```bash
# 获取 Let's Encrypt 证书
sudo certbot --nginx -d your-domain.com

# 自动续期
sudo certbot renew --dry-run
```

#### 3. 完整 HTTPS 配置

```nginx
server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # HSTS
    add_header Strict-Transport-Security "max-age=31536000" always;

    # 其他配置同上...
}

# HTTP 重定向到 HTTPS
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}
```

---

## 监控与日志

### 1. 日志配置

应用日志位置:

```
logs/
├── app.log           # 应用日志
├── error.log         # 错误日志
├── access.log        # 访问日志 (Nginx)
└── scheduler.log     # 调度器日志
```

### 2. 日志轮转

创建 `/etc/logrotate.d/akshare_web`:

```
/opt/akshare_web/logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    create 0640 akshare akshare
    sharedscripts
    postrotate
        systemctl reload akshare_web > /dev/null 2>&1 || true
    endscript
}
```

### 3. 健康检查

```bash
# 检查服务状态
curl http://localhost:8000/health

# 预期响应
{
    "status": "healthy",
    "version": "1.0.0",
    "database": "connected",
    "scheduler": "running"
}
```

### 4. 监控指标

可以集成的监控系统:

- **Prometheus + Grafana**: 指标收集和可视化
- **Sentry**: 错误追踪
- **ELK Stack**: 日志聚合分析

---

## 安全加固

### 1. 防火墙配置

```bash
# UFW (Ubuntu)
sudo ufw allow 22/tcp      # SSH
sudo ufw allow 80/tcp      # HTTP
sudo ufw allow 443/tcp     # HTTPS
sudo ufw deny 8000/tcp     # 不直接暴露后端
sudo ufw enable
```

### 2. 应用安全

- 修改默认管理员密码
- 使用强随机 `SECRET_KEY`
- 启用 HTTPS
- 配置 CORS 白名单
- 启用速率限制
- 定期更新依赖

### 3. 数据库安全

- 使用强密码
- 限制远程访问
- 定期备份
- 启用慢查询日志

---

## 故障排查

### 服务无法启动

1. 检查日志:
```bash
sudo journalctl -u akshare_web -n 50
```

2. 检查端口占用:
```bash
sudo netstat -tlnp | grep 8000
```

3. 检查数据库连接:
```bash
mysql -u akshare_user -p -h localhost akshare_web
```

### 数据库连接失败

1. 验证连接字符串
2. 检查 MySQL 服务状态
3. 验证用户权限
4. 检查防火墙规则

### 任务未执行

1. 检查调度器状态: `/health` 端点
2. 验证任务 `is_active=True`
3. 查看 `scheduler.log`
4. 检查 Cron 表达式语法

### 性能问题

1. 检查数据库慢查询
2. 增加worker数量
3. 启用 Redis 缓存
4. 使用连接池

---

## 升级指南

### 应用升级

```bash
# 备份
mysqldump -u root -p akshare_web > backup_$(date +%Y%m%d).sql

# 拉取新代码
git pull origin main

# 更新依赖
source venv/bin/activate
pip install -r requirements.txt

# 数据库迁移
alembic upgrade head

# 重启服务
sudo systemctl restart akshare_web
```

### 回滚

```bash
git checkout <previous-tag>
alembic downgrade <version>
sudo systemctl restart akshare_web
```

---

## 联系支持

如需帮助，请:
- 查看日志文件
- 检查 GitHub Issues
- 联系技术支持
