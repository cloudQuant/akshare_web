"""Retry utility for data fetch operations"""

import logging
import time
from functools import wraps


def retry_on_exception(
    max_retries: int = 3,
    retry_delay: int = 5,
    logger: logging.Logger | None = None,
    allowed_exceptions: tuple = (Exception,),
):
    """
    重试装饰器

    Args:
        max_retries: 最大重试次数
        retry_delay: 重试延迟（秒）
        logger: 日志记录器
        allowed_exceptions: 允许重试的异常类型
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            local_logger = logger
            if not local_logger and args and hasattr(args[0], "logger"):
                local_logger = args[0].logger

            if not local_logger:
                local_logger = logging.getLogger(func.__name__)

            last_exception = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except allowed_exceptions as e:
                    last_exception = e
                    local_logger.warning(
                        f"{func.__name__} 第 {attempt + 1}/{max_retries} 次执行失败: {e}"
                    )
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay * (2 ** attempt))  # 指数退避

            local_logger.error(f"{func.__name__} 执行失败，达到最大重试次数")
            raise last_exception

        return wrapper

    return decorator


def async_retry_on_exception(
    max_retries: int = 3,
    retry_delay: int = 5,
    logger: logging.Logger | None = None,
    allowed_exceptions: tuple = (Exception,),
):
    """
    异步重试装饰器

    Args:
        max_retries: 最大重试次数
        retry_delay: 重试延迟（秒）
        logger: 日志记录器
        allowed_exceptions: 允许重试的异常类型
    """

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            local_logger = logger
            if not local_logger and args and hasattr(args[0], "logger"):
                local_logger = args[0].logger

            if not local_logger:
                local_logger = logging.getLogger(func.__name__)

            last_exception = None
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except allowed_exceptions as e:
                    last_exception = e
                    local_logger.warning(
                        f"{func.__name__} 第 {attempt + 1}/{max_retries} 次执行失败: {e}"
                    )
                    if attempt < max_retries - 1:
                        import asyncio

                        await asyncio.sleep(retry_delay * (2 ** attempt))

            local_logger.error(f"{func.__name__} 执行失败，达到最大重试次数")
            raise last_exception

        return wrapper

    return decorator
