from datetime import datetime

from collection_compiler_service.config.ServiceConfig import stock_service_config
from common.utils.db.redis.AsyncRedisClient import AsyncRedisClient

_PREFIX = "ocr:progress"


def _key(file_hash: str) -> str:
    return f"{_PREFIX}:{file_hash}"


def _redis() -> AsyncRedisClient:
    cfg = stock_service_config
    return AsyncRedisClient(host=cfg.redis_host, port=cfg.redis_port,
                            password=cfg.redis_password, db=cfg.redis_database)


class OcrProgressRepository:

    async def is_running(self, file_hash: str) -> bool:
        async with _redis() as r:
            status = await r.async_hget(_key(file_hash), "status")
            return status == "running"

    async def start(self, file_hash: str, total: int, use_multimodal: bool = False) -> None:
        async with _redis() as r:
            client = await r._get_client()
            await client.hset(_key(file_hash), mapping={
                "status": "running",
                "mode": "multimodal" if use_multimodal else "ocr",
                "total": total,
                "done": 0,
                "failed": 0,
                "no_file": 0,
                "current_id": "",
                "current_uid": "",
                "current_application_code": "",
                "started_at": datetime.now().isoformat(timespec="seconds"),
            })

    async def set_current(self, file_hash: str, case_id: int, uid: str, application_code: str) -> None:
        async with _redis() as r:
            client = await r._get_client()
            await client.hset(_key(file_hash), mapping={
                "current_id": case_id,
                "current_uid": uid or "",
                "current_application_code": application_code or "",
            })

    async def inc_done(self, file_hash: str) -> None:
        async with _redis() as r:
            await (await r._get_client()).hincrby(_key(file_hash), "done", 1)

    async def inc_failed(self, file_hash: str) -> None:
        async with _redis() as r:
            await (await r._get_client()).hincrby(_key(file_hash), "failed", 1)

    async def inc_no_file(self, file_hash: str) -> None:
        async with _redis() as r:
            await (await r._get_client()).hincrby(_key(file_hash), "no_file", 1)

    async def finish(self, file_hash: str) -> None:
        async with _redis() as r:
            await (await r._get_client()).hset(_key(file_hash), "status", "done")

    async def delete(self, file_hash: str) -> bool:
        async with _redis() as r:
            return bool(await (await r._get_client()).delete(_key(file_hash)))

    async def get_progress(self, file_hash: str) -> dict | None:
        async with _redis() as r:
            data = await (await r._get_client()).hgetall(_key(file_hash))
        if not data:
            return None
        return {
            "file_hash": file_hash,
            "status": data.get("status"),
            "mode": data.get("mode"),
            "total": int(data.get("total", 0)),
            "done": int(data.get("done", 0)),
            "failed": int(data.get("failed", 0)),
            "no_file": int(data.get("no_file", 0)),
            "current_id": data.get("current_id"),
            "current_uid": data.get("current_uid"),
            "current_application_code": data.get("current_application_code"),
            "started_at": data.get("started_at"),
        }


    async def get_all_progress(self) -> list[dict]:
        results = []
        async with _redis() as r:
            client = await r._get_client()
            cursor = 0
            while True:
                cursor, keys = await client.scan(cursor, match=f"{_PREFIX}:*", count=100)
                for key in keys:
                    data = await client.hgetall(key)
                    if data:
                        file_hash = key.removeprefix(f"{_PREFIX}:")
                        results.append({
                            "file_hash": file_hash,
                            "status": data.get("status"),
                            "mode": data.get("mode"),
                            "total": int(data.get("total", 0)),
                            "done": int(data.get("done", 0)),
                            "failed": int(data.get("failed", 0)),
                            "no_file": int(data.get("no_file", 0)),
                            "current_id": data.get("current_id"),
                            "current_uid": data.get("current_uid"),
                            "current_application_code": data.get("current_application_code"),
                            "started_at": data.get("started_at"),
                        })
                if cursor == 0:
                    break
        return results


    async def get_interrupted_hashes(self) -> list[dict]:
        results = []
        async with _redis() as r:
            client = await r._get_client()
            cursor = 0
            while True:
                cursor, keys = await client.scan(cursor, match=f"{_PREFIX}:*", count=100)
                for key in keys:
                    data = await client.hmget(key, "status", "mode")
                    if data[0] in ("interrupted", "running"):
                        results.append({
                            "file_hash": key.removeprefix(f"{_PREFIX}:"),
                            "mode": data[1] or "multimodal",
                        })
                if cursor == 0:
                    break
        return results

    async def reset_for_retry(self, file_hash: str) -> None:
        async with _redis() as r:
            client = await r._get_client()
            await client.hset(_key(file_hash), mapping={
                "status": "running",
                "done": 0,
                "failed": 0,
                "no_file": 0,
                "current_id": "",
                "current_uid": "",
                "current_application_code": "",
                "started_at": datetime.now().isoformat(timespec="seconds"),
            })
        count = 0
        async with _redis() as r:
            client = await r._get_client()
            cursor = 0
            while True:
                cursor, keys = await client.scan(cursor, match=f"{_PREFIX}:*", count=100)
                for key in keys:
                    status = await client.hget(key, "status")
                    if status == "running":
                        await client.hset(key, "status", "interrupted")
                        count += 1
                if cursor == 0:
                    break
        return count


ocr_progress_repository = OcrProgressRepository()
