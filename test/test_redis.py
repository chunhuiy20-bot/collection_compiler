import sys
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from common.utils.db.redis.AsyncRedisClient import AsyncRedisClient

HOST = "8.130.81.134"
PORT = 6379
PASSWORD = "137139yang@"
DB = 3


async def main():
    async with AsyncRedisClient(host=HOST, port=PORT, password=PASSWORD, db=DB) as client:
        # 连接测试
        # print("ping:", await client.ping())

        # 存储字符串
        # await client.async_set("test:name", "张三", ex=60)
        print("get test:name:", await client.async_get("test:name"))

        # 存储 dict
        # await client.async_set("test:user", {"id": 1, "name": "李四"}, ex=60)
        print("get test:user:", await client.async_get("test:user", as_json=True))

        # 删除
        # await client.async_delete("test:name", "test:user")
        # print("after delete, test:name:", await client.async_get("test:name"))


if __name__ == "__main__":
    asyncio.run(main())
