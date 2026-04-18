"""
文件名: AsyncRedisClient.py
作者: yangchunhui
创建日期: 2026/2/10
联系方式: chunhuiy20@gmail.com
版本号: 1.0
更改时间: 2026/2/10 18:30
描述: 异步 Redis 客户端工具类，提供完整的 Redis 操作封装。支持 String、Hash、List、Set、Sorted Set、Bitmap 等数据结构操作，以及发布订阅功能。实现了连接池管理、资源自动清理、上下文管理器支持。

修改历史:
2026/2/10 18:30 - yangchunhui - 初始版本，重构原有代码，修复资源泄漏、类型安全等问题

依赖:
- typing: 提供类型注解支持（Optional, Union, Dict, Any, List）
- os: 环境变量读取
- json: JSON 序列化/反序列化
- redis.asyncio: 异步 Redis 客户端（Redis, ConnectionPool）
- contextlib: 异步上下文管理器支持

使用示例:
    # 方式1: 使用上下文管理器（推荐）
    async with AsyncRedisClient() as redis_client:
        await redis_client.async_set("key", "value", ex=60)
        value = await redis_client.async_get("key")

    # 方式2: 手动管理
    redis_client = AsyncRedisClient()
    try:
        await redis_client.async_set("key", {"data": "value"})
        data = await redis_client.async_get("key")
    finally:
        await redis_client.close()

    # 方式3: 使用装饰器（最简洁）
    @with_redis_client()
    async def my_function(redis_client: AsyncRedisClient):
        await redis_client.async_set("key", "value")
        return await redis_client.async_get("key")

    result = await my_function()  # 自动管理连接

    # 方式4: 装饰器指定配置
    @with_redis_client(db=1, max_connections=20)
    async def cache_user(user_id: int, redis_client: AsyncRedisClient):
        await redis_client.async_set(f"user:{user_id}", {"id": user_id})

    await cache_user(user_id=123)

    # 发布订阅示例
    async with AsyncRedisClient() as redis_client:
        await redis_client.publish("channel", {"event": "test"})

        async with redis_client.subscribe("channel") as pubsub:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    print(message["data"])
"""

import os
import json
from typing import Optional, Union, Dict, Any, List, Callable
from functools import wraps
from redis.asyncio import Redis as AsyncRedis, ConnectionPool as AsyncConnectionPool
from redis.exceptions import RedisError, ConnectionError, TimeoutError
from contextlib import asynccontextmanager


class RedisConfig:
    """Redis 配置类"""
    def __init__(
        self,
        host: str,
        port: int,
        password: Optional[str] = None,
        db: int = 0,
        max_connections: int = 10,
        decode_responses: bool = True,
        socket_timeout: int = 5,
        socket_connect_timeout: int = 5,
    ):
        self.host = host
        self.port = port
        self.password = password
        self.db = db
        self.max_connections = max_connections
        self.decode_responses = decode_responses
        self.socket_timeout = socket_timeout
        self.socket_connect_timeout = socket_connect_timeout


def with_redis_client(
    host: Optional[str] = None,
    port: Optional[int] = None,
    password: Optional[str] = None,
    db: Optional[int] = None,
    **kwargs
):
    """
    装饰器：自动管理 Redis 客户端生命周期

    被装饰的函数会自动获得一个 redis_client 参数，函数执行完毕后自动关闭连接。

    Args:
        host: Redis 主机地址
        port: Redis 端口
        password: Redis 密码
        db: Redis 数据库编号
        **kwargs: 其他 AsyncRedisClient 初始化参数

    使用示例:
        @with_redis_client()
        async def my_function(redis_client: AsyncRedisClient):
            await redis_client.async_set("key", "value")
            return await redis_client.async_get("key")

        # 调用时不需要传递 redis_client 参数
        result = await my_function()

        # 也可以指定配置
        @with_redis_client(db=1, max_connections=20)
        async def another_function(redis_client: AsyncRedisClient, user_id: int):
            await redis_client.async_set(f"user:{user_id}", "data")

        await another_function(user_id=123)
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **func_kwargs):
            async with AsyncRedisClient(
                host=host,
                port=port,
                password=password,
                db=db,
                **kwargs
            ) as redis_client:
                return await func(*args, redis_client=redis_client, **func_kwargs)
        return wrapper
    return decorator


class AsyncRedisClient:
    """
    异步 Redis 操作工具类

    提供完整的 Redis 数据结构操作封装，支持连接池管理和资源自动清理。
    """

    def __init__(
        self,
        config: Optional[RedisConfig] = None,
        host: Optional[str] = None,
        port: Optional[int] = None,
        password: Optional[str] = None,
        db: Optional[int] = None,
        max_connections: int = 10,
        decode_responses: bool = True,
        socket_timeout: int = 5,
        socket_connect_timeout: int = 5,
    ):
        """
        初始化 Redis 客户端

        Args:
            config: Redis 配置对象（优先使用）
            host: Redis 主机地址，默认从环境变量 REDIS_HOST 读取，fallback 为 localhost
            port: Redis 端口，默认从环境变量 REDIS_PORT 读取，fallback 为 6379
            password: Redis 密码，默认从环境变量 REDIS_PASSWORD 读取
            db: Redis 数据库编号，默认从环境变量 REDIS_DB 读取，fallback 为 0
            max_connections: 连接池最大连接数
            decode_responses: 是否自动解码响应为字符串
            socket_timeout: Socket 超时时间（秒）
            socket_connect_timeout: Socket 连接超时时间（秒）
        """
        # 如果提供了 config 对象，优先使用
        if config:
            self._host = config.host
            self._port = config.port
            self._password = config.password
            self._db = config.db
            self._max_connections = config.max_connections
            self._decode_responses = config.decode_responses
            self._socket_timeout = config.socket_timeout
            self._socket_connect_timeout = config.socket_connect_timeout
        else:
            # 从环境变量或参数获取配置，带类型转换和默认值
            self._host = host or os.getenv("REDIS_HOST", "localhost")
            self._port = port or int(os.getenv("REDIS_PORT", "6379"))
            self._password = password or os.getenv("REDIS_PASSWORD")
            self._db = db if db is not None else int(os.getenv("REDIS_DB", "0"))
            self._max_connections = max_connections
            self._decode_responses = decode_responses
            self._socket_timeout = socket_timeout
            self._socket_connect_timeout = socket_connect_timeout

        # 连接池和客户端实例（延迟初始化）
        self._async_pool: Optional[AsyncConnectionPool] = None
        self._async_client: Optional[AsyncRedis] = None

    async def _get_client(self) -> AsyncRedis:
        """
        获取或创建异步 Redis 客户端实例（单例模式）

        Returns:
            AsyncRedis: 异步 Redis 客户端实例
        """
        if self._async_client is None:
            if self._async_pool is None:
                self._async_pool = AsyncConnectionPool(
                    host=self._host,
                    port=self._port,
                    password=self._password,
                    db=self._db,
                    max_connections=self._max_connections,
                    decode_responses=self._decode_responses,
                    socket_timeout=self._socket_timeout,
                    socket_connect_timeout=self._socket_connect_timeout,
                )
            self._async_client = AsyncRedis(connection_pool=self._async_pool)
        return self._async_client

    async def close(self) -> None:
        """
        关闭 Redis 连接和连接池，释放资源
        """
        if self._async_client:
            await self._async_client.close()
            self._async_client = None
        if self._async_pool:
            await self._async_pool.disconnect()
            self._async_pool = None

    async def __aenter__(self):
        """异步上下文管理器入口"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器退出，自动清理资源"""
        await self.close()

    async def ping(self) -> bool:
        """
        检查 Redis 连接是否正常

        Returns:
            bool: 连接正常返回 True，否则返回 False
        """
        try:
            client = await self._get_client()
            return await client.ping()
        except (RedisError, ConnectionError, TimeoutError, OSError):
            return False

    # ============================================================
    # String 操作
    # ============================================================

    async def async_set(
        self,
        key: str,
        value: Union[str, dict, list, int, float],
        ex: Optional[int] = None,
        px: Optional[int] = None,
        nx: bool = False,
        xx: bool = False
    ) -> bool:
        """
        异步设置键值对

        Args:
            key: 键名
            value: 值，支持 str/dict/list/int/float，dict 和 list 会自动序列化为 JSON
            ex: 过期时间（秒）
            px: 过期时间（毫秒）
            nx: 仅当键不存在时设置
            xx: 仅当键存在时设置

        Returns:
            bool: 设置成功返回 True
        """
        if isinstance(value, (dict, list)):
            value = json.dumps(value, ensure_ascii=False)
        elif isinstance(value, (int, float)):
            value = str(value)

        client = await self._get_client()
        return await client.set(key, value, ex=ex, px=px, nx=nx, xx=xx)

    async def async_get(self, key: str, default: Any = None, as_json: bool = False) -> Any:
        """
        异步获取键值

        Args:
            key: 键名
            default: 键不存在时的默认值
            as_json: 是否尝试 JSON 反序列化

        Returns:
            Any: 键对应的值，键不存在返回 default
        """
        client = await self._get_client()
        value = await client.get(key)

        if value is None:
            return default

        if as_json:
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value

        return value

    async def async_delete(self, *keys: str) -> int:
        """
        异步删除一个或多个键

        Args:
            *keys: 要删除的键名

        Returns:
            int: 成功删除的键数量
        """
        client = await self._get_client()
        return await client.delete(*keys)

    async def async_exists(self, *keys: str) -> int:
        """
        异步检查键是否存在

        Args:
            *keys: 要检查的键名

        Returns:
            int: 存在的键数量
        """
        client = await self._get_client()
        return await client.exists(*keys)

    async def async_expire(self, key: str, seconds: int) -> bool:
        """
        异步为键设置过期时间

        Args:
            key: 键名
            seconds: 过期时间（秒）

        Returns:
            bool: 设置成功返回 True
        """
        client = await self._get_client()
        return await client.expire(key, seconds)

    async def async_ttl(self, key: str) -> int:
        """
        异步获取键的剩余过期时间

        Args:
            key: 键名

        Returns:
            int: 剩余秒数，-1 表示永不过期，-2 表示键不存在
        """
        client = await self._get_client()
        return await client.ttl(key)

    async def async_incr(self, key: str, amount: int = 1) -> int:
        """
        异步增加键的整数值

        Args:
            key: 键名
            amount: 增加的数量

        Returns:
            int: 增加后的值
        """
        client = await self._get_client()
        return await client.incrby(key, amount)

    async def async_decr(self, key: str, amount: int = 1) -> int:
        """
        异步减少键的整数值

        Args:
            key: 键名
            amount: 减少的数量

        Returns:
            int: 减少后的值
        """
        client = await self._get_client()
        return await client.decrby(key, amount)

    # ============================================================
    # Hash 操作
    # ============================================================

    async def async_hset(self, name: str, key: str, value: Any) -> int:
        """
        异步设置哈希字段

        Args:
            name: 哈希表名
            key: 字段名
            value: 字段值，dict 和 list 会自动序列化为 JSON

        Returns:
            int: 新增字段数量（0 或 1）
        """
        if isinstance(value, (dict, list)):
            value = json.dumps(value, ensure_ascii=False)
        client = await self._get_client()
        return await client.hset(name, key, value)

    async def async_hget(self, name: str, key: str, as_json: bool = False) -> Optional[Any]:
        """
        异步获取哈希字段

        Args:
            name: 哈希表名
            key: 字段名
            as_json: 是否尝试 JSON 反序列化

        Returns:
            Optional[Any]: 字段值，字段不存在返回 None
        """
        client = await self._get_client()
        value = await client.hget(name, key)

        if value is None:
            return None

        if as_json:
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value

        return value

    async def async_hgetall(self, name: str) -> Dict[str, Any]:
        """
        异步获取哈希表所有字段

        Args:
            name: 哈希表名

        Returns:
            Dict[str, Any]: 字段名到字段值的映射
        """
        client = await self._get_client()
        return await client.hgetall(name)

    async def async_hdel(self, name: str, *keys: str) -> int:
        """
        异步删除哈希字段

        Args:
            name: 哈希表名
            *keys: 要删除的字段名

        Returns:
            int: 成功删除的字段数量
        """
        client = await self._get_client()
        return await client.hdel(name, *keys)

    async def async_hexists(self, name: str, key: str) -> bool:
        """
        异步检查哈希字段是否存在

        Args:
            name: 哈希表名
            key: 字段名

        Returns:
            bool: 字段存在返回 True
        """
        client = await self._get_client()
        return await client.hexists(name, key)

    async def async_hkeys(self, name: str) -> List[str]:
        """
        异步获取哈希表所有字段名

        Args:
            name: 哈希表名

        Returns:
            List[str]: 字段名列表
        """
        client = await self._get_client()
        return await client.hkeys(name)

    async def async_hvals(self, name: str) -> List[Any]:
        """
        异步获取哈希表所有字段值

        Args:
            name: 哈希表名

        Returns:
            List[Any]: 字段值列表
        """
        client = await self._get_client()
        return await client.hvals(name)

    async def async_hlen(self, name: str) -> int:
        """
        异步获取哈希表字段数量

        Args:
            name: 哈希表名

        Returns:
            int: 字段数量
        """
        client = await self._get_client()
        return await client.hlen(name)

    # ============================================================
    # List 操作
    # ============================================================

    async def async_lpush(self, name: str, *values: Any) -> int:
        """
        异步从左侧插入列表元素

        Args:
            name: 列表名
            *values: 要插入的值

        Returns:
            int: 插入后列表长度
        """
        client = await self._get_client()
        return await client.lpush(name, *values)

    async def async_rpush(self, name: str, *values: Any) -> int:
        """
        异步从右侧插入列表元素

        Args:
            name: 列表名
            *values: 要插入的值

        Returns:
            int: 插入后列表长度
        """
        client = await self._get_client()
        return await client.rpush(name, *values)

    async def async_lpop(self, name: str, count: Optional[int] = None) -> Optional[Union[str, List[str]]]:
        """
        异步从左侧弹出列表元素

        Args:
            name: 列表名
            count: 弹出元素数量，None 表示弹出 1 个

        Returns:
            Optional[Union[str, List[str]]]: 弹出的元素，列表为空返回 None
        """
        client = await self._get_client()
        return await client.lpop(name, count)

    async def async_rpop(self, name: str, count: Optional[int] = None) -> Optional[Union[str, List[str]]]:
        """
        异步从右侧弹出列表元素

        Args:
            name: 列表名
            count: 弹出元素数量，None 表示弹出 1 个

        Returns:
            Optional[Union[str, List[str]]]: 弹出的元素，列表为空返回 None
        """
        client = await self._get_client()
        return await client.rpop(name, count)

    async def async_lrange(self, name: str, start: int, end: int) -> List[str]:
        """
        异步获取列表范围内的元素

        Args:
            name: 列表名
            start: 起始索引
            end: 结束索引（-1 表示到末尾）

        Returns:
            List[str]: 元素列表
        """
        client = await self._get_client()
        return await client.lrange(name, start, end)

    async def async_llen(self, name: str) -> int:
        """
        异步获取列表长度

        Args:
            name: 列表名

        Returns:
            int: 列表长度
        """
        client = await self._get_client()
        return await client.llen(name)

    # ============================================================
    # Set 操作
    # ============================================================

    async def async_sadd(self, name: str, *values: Any) -> int:
        """
        异步向集合添加元素

        Args:
            name: 集合名
            *values: 要添加的值

        Returns:
            int: 成功添加的元素数量
        """
        client = await self._get_client()
        return await client.sadd(name, *values)

    async def async_smembers(self, name: str) -> set:
        """
        异步获取集合所有成员

        Args:
            name: 集合名

        Returns:
            set: 成员集合
        """
        client = await self._get_client()
        return await client.smembers(name)

    async def async_srem(self, name: str, *values: Any) -> int:
        """
        异步从集合中移除元素

        Args:
            name: 集合名
            *values: 要移除的值

        Returns:
            int: 成功移除的元素数量
        """
        client = await self._get_client()
        return await client.srem(name, *values)

    async def async_sismember(self, name: str, value: Any) -> bool:
        """
        异步检查元素是否在集合中

        Args:
            name: 集合名
            value: 要检查的值

        Returns:
            bool: 元素存在返回 True
        """
        client = await self._get_client()
        return bool(await client.sismember(name, value))

    async def async_scard(self, name: str) -> int:
        """
        异步获取集合元素数量

        Args:
            name: 集合名

        Returns:
            int: 元素数量
        """
        client = await self._get_client()
        return await client.scard(name)

    # ============================================================
    # Sorted Set 操作
    # ============================================================

    async def async_zadd(self, name: str, mapping: Dict[str, float], nx: bool = False, xx: bool = False) -> int:
        """
        异步向有序集合添加成员

        Args:
            name: 有序集合名
            mapping: 成员到分数的映射 {member: score}
            nx: 仅添加新成员，不更新已存在成员
            xx: 仅更新已存在成员，不添加新成员

        Returns:
            int: 成功添加的成员数量
        """
        client = await self._get_client()
        return await client.zadd(name, mapping, nx=nx, xx=xx)

    async def async_zrange(
        self,
        name: str,
        start: int,
        end: int,
        desc: bool = False,
        withscores: bool = False
    ) -> List[Union[str, tuple]]:
        """
        异步获取有序集合范围内的成员

        Args:
            name: 有序集合名
            start: 起始索引
            end: 结束索引
            desc: 是否降序排列
            withscores: 是否返回分数

        Returns:
            List[Union[str, tuple]]: 成员列表，withscores=True 时返回 (member, score) 元组列表
        """
        client = await self._get_client()
        return await client.zrange(name, start, end, desc=desc, withscores=withscores)

    async def async_zrem(self, name: str, *values: Any) -> int:
        """
        异步从有序集合中移除成员

        Args:
            name: 有序集合名
            *values: 要移除的成员

        Returns:
            int: 成功移除的成员数量
        """
        client = await self._get_client()
        return await client.zrem(name, *values)

    async def async_zscore(self, name: str, value: Any) -> Optional[float]:
        """
        异步获取有序集合成员的分数

        Args:
            name: 有序集合名
            value: 成员

        Returns:
            Optional[float]: 成员分数，成员不存在返回 None
        """
        client = await self._get_client()
        return await client.zscore(name, value)

    async def async_zcard(self, name: str) -> int:
        """
        异步获取有序集合成员数量

        Args:
            name: 有序集合名

        Returns:
            int: 成员数量
        """
        client = await self._get_client()
        return await client.zcard(name)

    async def async_zrank(self, name: str, value: Any) -> Optional[int]:
        """
        异步获取有序集合成员的排名（升序）

        Args:
            name: 有序集合名
            value: 成员

        Returns:
            Optional[int]: 成员排名（从 0 开始），成员不存在返回 None
        """
        client = await self._get_client()
        return await client.zrank(name, value)

    # ============================================================
    # Bitmap 操作
    # ============================================================

    async def async_setbit(self, key: str, offset: int, value: int) -> int:
        """
        异步设置 bitmap 中指定偏移位的值

        Args:
            key: bitmap 键名
            offset: 偏移量
            value: 值（0 或 1）

        Returns:
            int: 该偏移位原来的值
        """
        client = await self._get_client()
        return await client.setbit(key, offset, value)

    async def async_getbit(self, key: str, offset: int) -> int:
        """
        异步获取 bitmap 中指定偏移位的值

        Args:
            key: bitmap 键名
            offset: 偏移量

        Returns:
            int: 该偏移位的值（0 或 1）
        """
        client = await self._get_client()
        return await client.getbit(key, offset)

    async def async_bitcount(self, key: str, start: int = 0, end: int = -1) -> int:
        """
        异步统计 bitmap 中值为 1 的位的数量

        Args:
            key: bitmap 键名
            start: 起始字节位置
            end: 结束字节位置

        Returns:
            int: 值为 1 的位的数量
        """
        client = await self._get_client()
        return await client.bitcount(key, start, end)

    async def async_bitop(self, operation: str, dest_key: str, *keys: str) -> int:
        """
        异步对多个 bitmap 进行位运算

        Args:
            operation: 位运算类型（AND, OR, XOR, NOT）
            dest_key: 结果存储的目标键
            *keys: 参与运算的源键

        Returns:
            int: 结果 bitmap 的长度（字节数）
        """
        client = await self._get_client()
        return await client.bitop(operation, dest_key, *keys)

    async def async_bitpos(self, key: str, bit: int, start: Optional[int] = None, end: Optional[int] = None) -> int:
        """
        异步查找 bitmap 中第一个指定值的位的位置

        Args:
            key: bitmap 键名
            bit: 要查找的位值（0 或 1）
            start: 起始字节位置
            end: 结束字节位置

        Returns:
            int: 第一个匹配位的位置，未找到返回 -1
        """
        client = await self._get_client()
        return await client.bitpos(key, bit, start, end)

    # ============================================================
    # 发布/订阅
    # ============================================================

    async def publish(self, channel: str, message: Union[str, dict, list]) -> int:
        """
        异步发布消息到频道

        Args:
            channel: 频道名
            message: 消息内容，dict 和 list 会自动序列化为 JSON

        Returns:
            int: 接收到消息的订阅者数量
        """
        if isinstance(message, (dict, list)):
            message = json.dumps(message, ensure_ascii=False)
        client = await self._get_client()
        return await client.publish(channel, message)

    @asynccontextmanager
    async def subscribe(self, *channels: str):
        """
        异步订阅频道（上下文管理器）

        Args:
            *channels: 要订阅的频道名

        Yields:
            PubSub: 发布订阅对象，可用于监听消息

        Example:
            async with redis_client.subscribe("channel1", "channel2") as pubsub:
                async for message in pubsub.listen():
                    if message["type"] == "message":
                        print(message["data"])
        """
        client = await self._get_client()
        pubsub = client.pubsub()
        try:
            await pubsub.subscribe(*channels)
            yield pubsub
        finally:
            await pubsub.unsubscribe(*channels)
            await pubsub.close()

    # ============================================================
    # 其他实用方法
    # ============================================================

    async def async_keys(self, pattern: str = "*") -> List[str]:
        """
        异步获取匹配模式的所有键（生产环境慎用，建议使用 scan）

        Args:
            pattern: 匹配模式

        Returns:
            List[str]: 键名列表
        """
        client = await self._get_client()
        return await client.keys(pattern)

    async def async_scan(self, cursor: int = 0, match: Optional[str] = None, count: int = 10) -> tuple:
        """
        异步迭代扫描键（推荐用于生产环境）

        Args:
            cursor: 游标位置
            match: 匹配模式
            count: 每次扫描的键数量建议值

        Returns:
            tuple: (下一个游标, 键列表)
        """
        client = await self._get_client()
        return await client.scan(cursor, match, count)

    async def async_flushdb(self, asynchronous: bool = False) -> bool:
        """
        异步清空当前数据库（危险操作，生产环境慎用）

        Args:
            asynchronous: 是否异步清空

        Returns:
            bool: 操作成功返回 True
        """
        client = await self._get_client()
        return await client.flushdb(asynchronous=asynchronous)

    async def async_dbsize(self) -> int:
        """
        异步获取当前数据库键数量

        Returns:
            int: 键数量
        """
        client = await self._get_client()
        return await client.dbsize()
