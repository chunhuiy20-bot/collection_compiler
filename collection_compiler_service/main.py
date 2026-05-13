import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .repository.OcrProgressRepository import ocr_progress_repository
from .repository.CaseAssignmentDetailRepository import CaseAssignmentDetailRepository
from .model.CaseAssignmentDetail import CaseAssignmentDetail as M
from .services.file_ocr_process_service import file_ocr_process_service, _background_tasks
from .router.excel_upload_router import router as excel_upload_router
from .router.chunk_upload_router import router as chunk_upload_router
from .router.file_search_router import router as file_search_router
from .router.file_upload_record_router import router as file_upload_record_router
from .router.file_ocr_router import router as file_ocr_router
from sqlalchemy import update

logger = logging.getLogger("collection_compiler_service")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup: 恢复上次被中断的任务
    interrupted = await ocr_progress_repository.get_interrupted_hashes()
    if interrupted:
        logger.info(f"发现 {len(interrupted)} 个中断任务，开始恢复: {interrupted}")
        file_hashes = [item["file_hash"] for item in interrupted]
        async with CaseAssignmentDetailRepository(db_name="collection_compiler") as repo:
            await repo.db.execute(
                update(M).where(M.file_hash.in_(file_hashes), M.case_status == 1).values(case_status=0)
            )
            await repo.db.commit()
        for item in interrupted:
            file_hash, mode = item["file_hash"], item["mode"]
            await ocr_progress_repository.reset_for_retry(file_hash)
            coro = (file_ocr_process_service.process_by_file_hash_multimodal(file_hash)
                    if mode == "multimodal" else file_ocr_process_service.process_by_file_hash(file_hash))
            t = asyncio.create_task(coro)
            _background_tasks[file_hash] = t
            t.add_done_callback(lambda _, fh=file_hash: _background_tasks.pop(fh, None))
            logger.info(f"file_hash={file_hash} mode={mode} 任务已重新启动")

    yield

    # shutdown: 标记运行中任务为 interrupted
    count = await ocr_progress_repository.cleanup_running()
    if count:
        logger.info(f"程序关闭，已将 {count} 个运行中的 OCR 任务标记为 interrupted")


app = FastAPI(
    title="Collection Compiler Service",
    version="0.1.0",
    description="Collection Compiler Service 后端接口服务",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(excel_upload_router)
app.include_router(chunk_upload_router)
app.include_router(file_search_router)
app.include_router(file_upload_record_router)
app.include_router(file_ocr_router)


@app.get("/health")
def health() -> dict[str, Any]:
    return {"status": "ok"}
