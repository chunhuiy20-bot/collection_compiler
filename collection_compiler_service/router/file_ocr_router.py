import asyncio
from typing import Any

from fastapi import HTTPException, Query

from common.schemas.CommonResult import Result
from common.utils.router.CustomRouter import CustomAPIRouter
from ..services.file_ocr_process_service import file_ocr_process_service, _background_tasks

router = CustomAPIRouter(
    prefix="/api/v1/ocr",
    tags=["OCR/多模态 处理文件"],
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


@router.post("/process/batch", summary="按批量用户 uid 处理待处理案件的 OCR 识别")
async def process_ocr_by_uids(uids: list[str] = Query(...), use_multimodal: bool = False) -> Result[Any]:
    if not uids:
        raise HTTPException(status_code=400, detail="uids 不能为空")
    task = (file_ocr_process_service.process_by_uids_multimodal(uids)
            if use_multimodal else file_ocr_process_service.process_by_uids(uids))
    t = asyncio.create_task(task)
    _background_tasks.add(t)
    t.add_done_callback(_background_tasks.discard)
    msg = "多模态任务已启动" if use_multimodal else "OCR 任务已启动"
    return Result.success(data={"uids": uids}, message=msg)