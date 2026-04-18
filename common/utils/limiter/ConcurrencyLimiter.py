"""
文件名: ConcurrencyLimiter.py
作者: yangchunhui
创建日期: 2026/2/10
联系方式: chunhuiy20@gmail.com
版本号: 1.0
更改时间: 2026/2/10
描述: 基于 asyncio.Semaphore 的并发控制工具，支持请求排队

修改历史:
2026/2/10 - yangchunhui - 初始版本

依赖:
- asyncio: Python 异步库

使用示例:
from common.utils.limiter.ConcurrencyLimiter import concurrency_limiter

@router.get("/test")
@concurrency_limiter(max_concurrent=10)  # 最多10个并发，超出的请求排队等待
async def test():
    return {"message": "success"}
"""

import asyncio
import time
from functools import wraps
from typing import Optional, Callable


class ConcurrencyLimiter:
    """
    并发限制器
    使用信号量控制并发数，超出限制的请求会排队等待
    """

    def __init__(self, max_concurrent: int = 10, timeout: Optional[float] = None):
        """
        初始化并发限制器

        Args:
            max_concurrent: 最大并发数
            timeout: 等待超时时间（秒），None 表示无限等待
        """
        self.max_concurrent = max_concurrent
        self.timeout = timeout
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.waiting_count = 0
        self.total_requests = 0
        self.rejected_requests = 0

    async def acquire(self) -> bool:
        """
        获取信号量

        Returns:
            bool: 是否成功获取
        """
        self.total_requests += 1
        self.waiting_count += 1

        try:
            if self.timeout:
                await asyncio.wait_for(
                    self.semaphore.acquire(),
                    timeout=self.timeout
                )
            else:
                await self.semaphore.acquire()

            self.waiting_count -= 1
            return True

        except asyncio.TimeoutError:
            self.waiting_count -= 1
            self.rejected_requests += 1
            return False

    def release(self):
        """释放信号量"""
        self.semaphore.release()

    def get_stats(self) -> dict:
        """
        获取统计信息

        Returns:
            dict: 统计信息
        """
        return {
            "max_concurrent": self.max_concurrent,
            "waiting_count": self.waiting_count,
            "total_requests": self.total_requests,
            "rejected_requests": self.rejected_requests,
            "available_slots": self.max_concurrent - (self.semaphore._value if hasattr(self.semaphore, '_value') else 0)
        }

    def __call__(self, func: Callable):
        """
        装饰器：为函数添加并发控制

        Args:
            func: 要装饰的异步函数

        Returns:
            装饰后的函数
        """
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 尝试获取信号量
            acquired = await self.acquire()

            if not acquired:
                # 超时，返回 503 错误
                from fastapi import HTTPException
                raise HTTPException(
                    status_code=503,
                    detail=f"服务繁忙，请稍后重试。当前排队: {self.waiting_count}"
                )

            try:
                # 执行原函数
                start_time = time.time()
                result = await func(*args, **kwargs)
                elapsed = time.time() - start_time

                # 可以在这里添加日志
                # print(f"请求完成，耗时: {elapsed:.3f}s")

                return result

            finally:
                # 释放信号量
                self.release()

        return wrapper


# 创建全局并发限制器实例
# 可以根据不同的业务场景创建多个限制器
default_limiter = ConcurrencyLimiter(max_concurrent=10, timeout=30.0)  # 最多10个并发，等待超时30秒
heavy_limiter = ConcurrencyLimiter(max_concurrent=3, timeout=60.0)     # 重量级任务：最多3个并发
light_limiter = ConcurrencyLimiter(max_concurrent=50, timeout=10.0)    # 轻量级任务：最多50个并发


def concurrency_limit(max_concurrent: int = 10, timeout: Optional[float] = 30.0):
    """
    并发限制装饰器工厂函数

    Args:
        max_concurrent: 最大并发数
        timeout: 等待超时时间（秒）

    Returns:
        装饰器函数

    使用示例:
        @concurrency_limit(max_concurrent=5, timeout=10.0)
        async def my_handler():
            pass
    """
    limiter = ConcurrencyLimiter(max_concurrent=max_concurrent, timeout=timeout)
    return limiter