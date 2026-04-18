"""
文件名: AsyncDecorators.py
作者: yangchunhui
创建日期: 2026/2/9
联系方式: chunhuiy20@gmail.com
版本号: 1.0
更改时间: 2026/2/9
描述: 通用异步装饰器集合

修改历史:
2026/2/9 - yangchunhui - 初始版本，从 BaseEmailSender 中提取 async_retry 装饰器

依赖:
- asyncio: 异步支持
- functools: 装饰器工具
"""

import asyncio
from functools import wraps


def async_retry(max_retries: int = 3, delay: float = 1.0):
    """
    异步重试装饰器

    当异步函数执行失败时自动重试，适用于网络请求、数据库操作等可能临时失败的场景。

    Args:
        max_retries: 最大重试次数，默认 3 次
        delay: 每次重试之间的延迟时间（秒），默认 1.0 秒

    Returns:
        装饰后的异步函数

    Raises:
        Exception: 如果所有重试都失败，抛出最后一次的异常

    使用示例:
        @async_retry(max_retries=3, delay=1.0)
        async def fetch_data():
            # 可能失败的异步操作
            return await some_async_operation()
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        await asyncio.sleep(delay)
            raise last_exception
        return wrapper
    return decorator
