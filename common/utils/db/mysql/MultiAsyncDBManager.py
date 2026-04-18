"""
文件名: MultiAsyncDBManager.py
作者: yangchunhui
创建日期: 2026/2/6
联系方式: chunhuiy20@gmail.com
版本号: 1.0
更改时间: 2026/2/6 11:34
描述: 多数据库异步连接管理器，提供多数据库连接池管理、会话管理、健康检查等功能。
支持同时管理多个数据库连接，每个数据库独立配置连接池参数。
包含 MultiAsyncDBManager（多数据库管理器）和 AsyncDBManager（单数据库管理器）。

修改历史:
2026/2/6 11:34 - yangchunhui - 初始版本

依赖:
- os: 环境变量读取，用于获取数据库配置
- time: 时间操作，用于记录数据库管理器启动时间
- contextlib: asynccontextmanager 装饰器，用于创建异步上下文管理器
- typing: 类型注解支持（AsyncGenerator, Dict, Optional）
- sqlalchemy.ext.asyncio: 异步数据库引擎和会话（create_async_engine, AsyncSession, async_sessionmaker）
- sqlalchemy.pool: AsyncAdaptedQueuePool，异步连接池实现
- dotenv: load_dotenv，用于加载 .env 环境变量文件
- asyncio: 异步锁和信号量（Lock, Semaphore），用于并发控制
- sqlalchemy: text，用于执行原生 SQL 语句（健康检查）
"""


import os
import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Dict, Optional
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import AsyncAdaptedQueuePool
from dotenv import load_dotenv
import asyncio
from sqlalchemy import text

load_dotenv()


class MultiAsyncDBManager:
    def __init__(self):
        self.databases: Dict[str, AsyncDBManager] = {}
        self.default_db: Optional[str] = None

    def add_database(self, name: str, database_url: str, **kwargs) -> 'AsyncDBManager':
        """添加数据库连接"""
        db_manager = AsyncDBManager(database_url=database_url, **kwargs)
        self.databases[name] = db_manager

        # 第一个添加的数据库作为默认数据库
        if self.default_db is None:
            self.default_db = name

        return db_manager

    def get_db(self, name: Optional[str] = None) -> 'AsyncDBManager':
        """获取指定数据库管理器"""
        db_name = name or self.default_db
        if db_name not in self.databases:
            raise ValueError(f"数据库 '{db_name}' 未配置")
        return self.databases[db_name]

    @asynccontextmanager
    async def session(self, db_name: Optional[str] = None) -> AsyncGenerator[AsyncSession, None]:
        """获取指定数据库的会话"""
        db_manager = self.get_db(db_name)
        async with db_manager.session() as session:
            yield session

    async def cleanup_all(self):
        """清理所有数据库连接"""
        for db_manager in self.databases.values():
            await db_manager.cleanup()


class AsyncDBManager:
    def __init__(self, database_url: Optional[str] = None, **config):
        # 如果没有传入 database_url，从环境变量读取
        self.DATABASE_URL = database_url or os.getenv("MYSQL_CONFIG_ASYNC")

        # 配置参数，支持传入覆盖
        self.POOL_SIZE = config.get("pool_size", int(os.getenv("DB_POOL_SIZE", "20")))
        self.MAX_OVERFLOW = config.get("max_overflow", int(os.getenv("DB_MAX_OVERFLOW", "10")))
        self.POOL_TIMEOUT = config.get("pool_timeout", int(os.getenv("DB_POOL_TIMEOUT", "30")))
        self.POOL_RECYCLE = config.get("pool_recycle", int(os.getenv("DB_POOL_RECYCLE", "1800")))

        # 创建异步引擎
        self.engine = create_async_engine(
            self.DATABASE_URL,
            poolclass=AsyncAdaptedQueuePool,
            pool_size=self.POOL_SIZE,
            max_overflow=self.MAX_OVERFLOW,
            pool_timeout=self.POOL_TIMEOUT,
            pool_recycle=self.POOL_RECYCLE,
            pool_pre_ping=True,
            echo=config.get("echo", True),
        )

        # 会话工厂
        self.SessionLocal = async_sessionmaker(
            class_=AsyncSession,
            autocommit=False,
            autoflush=False,
            bind=self.engine,
            expire_on_commit=False
        )

        # 统计信息
        self.start_time = time.time()
        self._lock = asyncio.Lock()
        self._semaphore = asyncio.Semaphore(self.POOL_SIZE)

    async def get_pool_status(self) -> dict:
        """获取连接池状态"""
        pool = self.engine.sync_engine.pool  # type: ignore[attr-defined]
        return {
            "pool_size": pool.size(),
            "checked_in": pool.checkedin(),
            "overflow": pool.overflow(),
            "checked_out": pool.checkedout(),
        }

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        """上下文方式获取会话"""
        async with self.SessionLocal() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    async def cleanup(self):
        """释放引擎资源"""
        await self.engine.dispose()

    async def check_health(self) -> bool:
        """健康检查"""
        try:
            async with self.session() as db:
                await db.execute(text("SELECT 1"))
            return True
        except Exception as e:
            print(f"[DB] 健康检查失败: {e}")
            return False


# 创建多数据库管理器
multi_db = MultiAsyncDBManager()

# 添加不同的数据库
# multi_db.add_database("main", os.getenv("MYSQL_CONFIG_ASYNC"))
# multi_db.add_database("db2", os.getenv("MYSQL_CONFIG_ASYNC2"))
# multi_db.add_database("finance_db", os.getenv("MYSQL_CONFIG_ASYNC_FINANCE_DB"))
