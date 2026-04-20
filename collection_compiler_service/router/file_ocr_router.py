import asyncio
from typing import Any

from fastapi import HTTPException

from common.schemas.CommonResult import Result
from common.utils.router.CustomRouter import CustomAPIRouter
from ..services.file_ocr_process_service import file_ocr_process_service

router = CustomAPIRouter(
    prefix="/api/v1/ocr",
    tags=["OCR 处理"],
    auto_log=True,
    logger_name="collection-compiler-service",
)


@router.post("/process", summary="按 file_hash 处理待处理案件的 OCR 识别")
async def process_ocr(file_hash: str, use_multimodal: bool = False) -> Result[Any]:
    if not file_hash:
        raise HTTPException(status_code=400, detail="file_hash 不能为空")
    if use_multimodal:
        asyncio.create_task(file_ocr_process_service.process_by_file_hash_multimodal(file_hash))
        return Result.success(data={"file_hash": file_hash}, message="多模态任务已启动")
    asyncio.create_task(file_ocr_process_service.process_by_file_hash(file_hash))
    return Result.success(data={"file_hash": file_hash}, message="OCR 任务已启动")