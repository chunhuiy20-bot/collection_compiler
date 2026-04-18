"""
文件名: WithRepoDecorators.py
作者: yangchunhui
创建日期: 2026/2/9
联系方式: chunhuiy20@gmail.com
版本号: 1.0
更改时间: 2026/2/9 15:00
描述: Repository 自动注入装饰器，用于在 Service 层方法中自动创建和注入 Repository 实例。解决异步环境下 Repository 实例共享导致的并发冲突问题，每次方法调用都会创建新的 Repository 实例，确保线程安全。

修改历史:
2026/2/9 15:00 - yangchunhui - 初始版本

依赖:
- typing: 提供类型注解支持（Type, Callable）
- functools: wraps 装饰器，用于保持被装饰函数的元数据
- common.utils.db.AsyncBaseRepository: 异步仓储基类

使用示例:
    from common.utils.decorators.WithRepoDecorators import with_repo
    from account_service.repository.UserRepository import UserRepository

    class UserService:
        @with_repo(UserRepository, db_name="main")
        async def get_user_list(self, user_repo: UserRepository):
            user_list = await user_repo.list()
            return Result.success(user_list)

        @with_repo(UserRepository, db_name="main")
        async def get_user_by_id(self, user_repo: UserRepository, user_id: int):
            user = await user_repo.get_by_id(user_id)
            return Result.success(user)
"""

from typing import Type, Callable
from functools import wraps


def with_repo(repo_class: Type, db_name: str = "main"):
    """
    Repository 自动注入装饰器

    自动为 Service 方法创建并注入 Repository 实例，避免全局单例导致的并发冲突。
    每次方法调用都会创建新的 Repository 实例，确保请求隔离。

    Args:
        repo_class: Repository 类（如 UserRepository）
        db_name: 数据库名称，默认为 "main"

    Returns:
        装饰后的函数

    Example:
        @with_repo(UserRepository, db_name="main")
        async def get_user_list(self, user_repo: UserRepository):
            return await user_repo.list()

    注意:
        - 被装饰的方法第一个参数（self 之后）必须是 Repository 类型
        - 装饰器会自动创建 Repository 实例并传入该参数
        - 每次调用都会创建新实例，不会有并发冲突
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            # 创建新的 Repository 实例
            repo = repo_class(db_name=db_name)
            # 将 repo 作为第一个参数传入
            return await func(self, repo, *args, **kwargs)
        return wrapper
    return decorator
