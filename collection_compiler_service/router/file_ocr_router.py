import asyncio
from typing import Any

from fastapi import HTTPException, Query

from common.schemas.CommonResult import Result
from common.utils.router.CustomRouter import CustomAPIRouter
from ..services.file_ocr_process_service import file_ocr_process_service, _background_tasks, _internal_tasks
from ..repository.OcrProgressRepository import ocr_progress_repository

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
    if await ocr_progress_repository.is_running(file_hash):
        raise HTTPException(status_code=409, detail="该 file_hash 正在处理中")
    coro = (file_ocr_process_service.process_by_file_hash_multimodal(file_hash)
            if use_multimodal else file_ocr_process_service.process_by_file_hash(file_hash))
    t = asyncio.create_task(coro)
    _background_tasks[file_hash] = t
    t.add_done_callback(lambda _: _background_tasks.pop(file_hash, None))
    msg = "多模态任务已启动" if use_multimodal else "OCR 任务已启动"
    return Result.success(data={"file_hash": file_hash}, message=msg)


@router.post("/process/batch", summary="按批量用户 uid 处理待处理案件的 OCR 识别")
async def process_ocr_by_uids(uids: list[str] = Query(...), use_multimodal: bool = False) -> Result[Any]:
    if not uids:
        raise HTTPException(status_code=400, detail="uids 不能为空")
    task = (file_ocr_process_service.process_by_uids_multimodal(uids)
            if use_multimodal else file_ocr_process_service.process_by_uids(uids))
    t = asyncio.create_task(task)
    _internal_tasks.add(t)
    t.add_done_callback(_internal_tasks.discard)
    msg = "多模态任务已启动" if use_multimodal else "OCR 任务已启动"
    return Result.success(data={"uids": uids}, message=msg)


@router.get("/progress", summary="查询 file_hash 的 OCR 处理进度")
async def get_ocr_progress(file_hash: str) -> Result[Any]:
    if not file_hash:
        raise HTTPException(status_code=400, detail="file_hash 不能为空")
    progress = await ocr_progress_repository.get_progress(file_hash)
    if progress is None:
        raise HTTPException(status_code=404, detail="未找到该 file_hash 的处理记录")
    return Result.success(data=progress)


@router.get("/progress/all", summary="查询所有 OCR 任务的处理进度")
async def get_all_ocr_progress() -> Result[Any]:
    return Result.success(data=await ocr_progress_repository.get_all_progress())


@router.delete("/progress", summary="删除 file_hash 的 OCR 处理记录")
async def delete_ocr_progress(file_hash: str) -> Result[Any]:
    if not file_hash:
        raise HTTPException(status_code=400, detail="file_hash 不能为空")
    if t := _background_tasks.get(file_hash):
        t.cancel()
    if not await ocr_progress_repository.delete(file_hash):
        raise HTTPException(status_code=404, detail="未找到该 file_hash 的处理记录")
    return Result.success()
