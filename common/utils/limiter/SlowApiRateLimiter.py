"""
文件名: SlowApiRateLimiter.py
作者: yangchunhui
创建日期: 2026/2/10
联系方式: chunhuiy20@gmail.com
版本号: 1.0
更改时间: 2026/2/10
描述: 基于 slowapi 的限流工具类，提供流量控制和请求排队功能

修改历史:
2026/2/10 - yangchunhui - 初始版本

依赖:
- slowapi: 限流库
- fastapi: Web 框架

使用示例:
from common.utils.limiter.RateLimiter import limiter, get_remote_address

@router.get("/test")
@limiter.limit("5/minute")  # 每分钟最多5个请求
async def test(request: Request):
    return {"message": "success"}
"""
from slowapi import Limiter
from slowapi.util import get_remote_address
from fastapi import Request


def get_user_identifier(request: Request) -> str:
    """
    获取用户标识符，用于限流
    优先级: 用户ID > IP地址

    Args:
        request: FastAPI 请求对象

    Returns:
        str: 用户标识符
    """
    # 如果有用户认证信息，使用用户ID
    if hasattr(request.state, "user_id"):
        return f"user:{request.state.user_id}"

    # 否则使用IP地址
    return get_remote_address(request)


# 创建全局限流器实例
limiter = Limiter(
    key_func=get_user_identifier,  # 使用自定义的标识符函数
    default_limits=["200/minute"],  # 全局默认限制：每分钟200个请求
    storage_uri="memory://",  # 使用内存存储（单机模式）
    # 如果需要分布式限流，可以使用 Redis:
    # storage_uri="redis://localhost:6379",
    strategy="fixed-window",  # 固定窗口策略
    # 其他可选策略:
    # - "fixed-window": 固定时间窗口
    # - "moving-window": 滑动时间窗口（更精确但消耗更多资源）
)
