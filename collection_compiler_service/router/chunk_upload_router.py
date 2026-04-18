from typing import Any

from fastapi import File, Form, UploadFile

from common.schemas.CommonResult import Result
from common.utils.router.CustomRouter import CustomAPIRouter
from ..services.chunk_upload_service import chunk_upload_service

router = CustomAPIRouter(
    prefix="/api/v1/upload",
    tags=["分片上传"],
    auto_log=True,
    logger_name="collection-compiler-service",
)


@router.post("/init", summary="初始化分片上传")
async def init_upload(
    upload_id: str = Form(...),
    filename: str = Form(...),
    total_chunks: int = Form(...),
    file_hash: str | None = Form(None),
) -> Result[Any]:
    data = await chunk_upload_service.init_upload(upload_id, filename, total_chunks, file_hash)
    return Result.success(data)


@router.post("/chunk", summary="上传单个分片")
async def upload_chunk(
    upload_id: str = Form(...),
    chunk_index: int = Form(...),
    chunk: UploadFile = File(...),
) -> Result[Any]:
    chunk_data = await chunk.read()
    data = await chunk_upload_service.upload_chunk(upload_id, chunk_index, chunk_data)
    return Result.success(data)


@router.post("/merge", summary="合并分片")
async def merge_chunks(
    upload_id: str = Form(...),
) -> Result[Any]:
    data = await chunk_upload_service.merge_chunks(upload_id)
    return Result.success(data)