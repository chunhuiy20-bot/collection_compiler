import asyncio
import json
import logging
import os
import shutil
import zipfile
from pathlib import Path
from typing import Any

from fastapi import HTTPException

from collection_compiler_service.model.FileUploadRecord import FileUploadRecord
from collection_compiler_service.repository.FileUploadRecordRepository import FileUploadRecordRepository

logger = logging.getLogger("collection_compiler_service")

# 临时分片目录，相对于项目根目录
TMP_DIR = Path("tmp/chunks")
UPLOAD_DIR = Path("uploads")


class ChunkUploadService:

    def init_dirs(self) -> None:
        TMP_DIR.mkdir(parents=True, exist_ok=True)
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------ #
    # 1. 初始化上传                                                         #
    # ------------------------------------------------------------------ #
    async def init_upload(self, upload_id: str, filename: str, total_chunks: int, file_hash: str | None = None) -> dict[str, Any]:
        self.init_dirs()

        # 秒传：hash 命中已有文件
        if file_hash:
            repo = FileUploadRecordRepository(db_name="collection_compiler")
            async with repo as repository:
                existing = await repository.find_by_hash(file_hash)
            if existing and Path(existing.file_path).exists():
                logger.info("秒传命中: hash=%s -> %s", file_hash, existing.file_path)
                return {"upload_id": upload_id, "filename": filename, "file_path": existing.file_path, "instant": True}

        upload_dir = TMP_DIR / upload_id

        # 已存在：断点续传，返回已上传的分片列表
        if upload_dir.exists():
            meta = self._read_meta(upload_dir)
            uploaded = self._uploaded_chunks(upload_dir, total_chunks)
            return {
                "upload_id": upload_id,
                "filename": meta.get("filename", filename),
                "total_chunks": meta.get("total_chunks", total_chunks),
                "uploaded_chunks": uploaded,
                "resumed": True,
            }

        upload_dir.mkdir(parents=True)
        meta = {"filename": filename, "total_chunks": total_chunks, "file_hash": file_hash}
        self._write_meta(upload_dir, meta)

        return {
            "upload_id": upload_id,
            "filename": filename,
            "total_chunks": total_chunks,
            "uploaded_chunks": [],
            "resumed": False,
        }

    # ------------------------------------------------------------------ #
    # 2. 上传单个分片                                                       #
    # ------------------------------------------------------------------ #
    async def upload_chunk(self, upload_id: str, chunk_index: int, chunk_data: bytes) -> dict[str, Any]:
        upload_dir = TMP_DIR / upload_id
        if not upload_dir.exists():
            raise HTTPException(status_code=400, detail=f"upload_id {upload_id} 不存在，请先初始化上传")

        part_path = upload_dir / f"{chunk_index}.part"
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, part_path.write_bytes, chunk_data)

        meta = self._read_meta(upload_dir)
        total_chunks = meta.get("total_chunks", 0)
        uploaded = self._uploaded_chunks(upload_dir, total_chunks)

        logger.info("分片上传: upload_id=%s chunk=%s/%s", upload_id, chunk_index + 1, total_chunks)

        return {
            "upload_id": upload_id,
            "chunk_index": chunk_index,
            "uploaded_chunks": uploaded,
            "total_chunks": total_chunks,
            "completed": len(uploaded) == total_chunks,
        }

    # ------------------------------------------------------------------ #
    # 3. 合并分片                                                           #
    # ------------------------------------------------------------------ #
    async def merge_chunks(self, upload_id: str) -> dict[str, Any]:
        upload_dir = TMP_DIR / upload_id
        if not upload_dir.exists():
            raise HTTPException(status_code=400, detail=f"upload_id {upload_id} 不存在")

        meta = self._read_meta(upload_dir)
        filename: str = meta.get("filename", f"{upload_id}.zip")
        total_chunks: int = meta.get("total_chunks", 0)
        file_hash: str | None = meta.get("file_hash")

        # 校验所有分片是否齐全
        missing = [i for i in range(total_chunks) if not (upload_dir / f"{i}.part").exists()]
        if missing:
            raise HTTPException(status_code=400, detail=f"分片缺失: {missing}")

        self.init_dirs()
        dest_path = UPLOAD_DIR / filename

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._merge_files, upload_dir, total_chunks, dest_path)

        # 清理临时目录
        shutil.rmtree(upload_dir, ignore_errors=True)

        file_size = dest_path.stat().st_size
        logger.info("合并完成: %s, 大小: %s bytes", filename, file_size)

        result: dict[str, Any] = {
            "upload_id": upload_id,
            "filename": filename,
            "file_path": str(dest_path),
            "file_size": file_size,
            "extracted": False,
        }

        if zipfile.is_zipfile(dest_path):
            extract_dir = UPLOAD_DIR / dest_path.stem
            await loop.run_in_executor(None, self._extract_zip, dest_path, extract_dir)
            logger.info("解压完成: %s -> %s", filename, extract_dir)
            result["extracted"] = True
            result["extract_path"] = str(extract_dir)

        if file_hash:
            await self._save_record(
                file_hash=file_hash,
                filename=filename,
                file_path=str(dest_path),
                file_size=file_size,
                file_type="zip" if zipfile.is_zipfile(dest_path) else "other",
            )

        return result

    # ------------------------------------------------------------------ #
    # 内部工具方法                                                          #
    # ------------------------------------------------------------------ #
    @staticmethod
    async def _save_record(file_hash: str, filename: str, file_path: str, file_size: int, file_type: str) -> None:
        repo = FileUploadRecordRepository(db_name="collection_compiler")
        async with repo as repository:
            existing = await repository.find_by_hash(file_hash)
            if existing:
                return
            entity = FileUploadRecord(
                file_hash=file_hash,
                filename=filename,
                file_path=file_path,
                file_size=file_size,
                file_type=file_type,
            )
            await repository.save(entity)

    @staticmethod
    def _extract_zip(zip_path: Path, extract_dir: Path) -> None:
        extract_dir.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(extract_dir)

    @staticmethod
    def _merge_files(upload_dir: Path, total_chunks: int, dest_path: Path) -> None:
        with open(dest_path, "wb") as out:
            for i in range(total_chunks):
                part = upload_dir / f"{i}.part"
                with open(part, "rb") as f:
                    shutil.copyfileobj(f, out)

    @staticmethod
    def _read_meta(upload_dir: Path) -> dict:
        meta_path = upload_dir / "meta.json"
        if meta_path.exists():
            return json.loads(meta_path.read_text(encoding="utf-8"))
        return {}

    @staticmethod
    def _write_meta(upload_dir: Path, meta: dict) -> None:
        (upload_dir / "meta.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")

    @staticmethod
    def _uploaded_chunks(upload_dir: Path, total_chunks: int) -> list[int]:
        return [i for i in range(total_chunks) if (upload_dir / f"{i}.part").exists()]


chunk_upload_service = ChunkUploadService()