"""Configuration for data fetch module"""

from app.core.config import settings

# Data database configuration (separate from app database)
DATA_DB_CONFIG = {
    "host": settings.data_db_host if hasattr(settings, "data_db_host") else "localhost",
    "port": settings.data_db_port if hasattr(settings, "data_db_port") else 3306,
    "user": settings.data_db_user if hasattr(settings, "data_db_user") else "root",
    "password": settings.data_db_password if hasattr(settings, "data_db_password") else "",
    "database": settings.data_db_name if hasattr(settings, "data_db_name") else "akshare_data",
    "charset": "utf8mb4",
}

# Script categories configuration
SCRIPT_CATEGORIES = {
    "stocks": {
        "name": "股票",
        "sub_categories": ["daily", "weekly", "monthly", "hourly"],
    },
    "funds": {
        "name": "基金",
        "sub_categories": ["daily", "weekly", "monthly", "hourly"],
    },
    "futures": {
        "name": "期货",
        "sub_categories": ["daily", "weekly", "monthly", "hourly"],
    },
    "indexs": {
        "name": "指数",
        "sub_categories": ["daily", "weekly", "monthly"],
    },
    "options": {
        "name": "期权",
        "sub_categories": ["daily", "weekly", "monthly", "hourly"],
    },
    "bonds": {
        "name": "债券",
        "sub_categories": ["daily", "weekly", "monthly", "hourly"],
    },
    "currencies": {
        "name": "外汇",
        "sub_categories": ["daily", "weekly", "monthly", "hourly"],
    },
    "forexs": {
        "name": "外汇",
        "sub_categories": ["daily", "weekly", "monthly", "hourly"],
    },
    "cryptos": {
        "name": "加密货币",
        "sub_categories": ["daily", "weekly", "monthly", "hourly"],
    },
    "common": {
        "name": "通用",
        "sub_categories": ["daily", "weekly", "monthly", "hourly"],
    },
}
