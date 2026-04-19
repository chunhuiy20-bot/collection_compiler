import logging
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .router.excel_upload_router import router as excel_upload_router
from .router.chunk_upload_router import router as chunk_upload_router
from .router.file_search_router import router as file_search_router
from .router.file_upload_record_router import router as file_upload_record_router
from .router.file_ocr_router import router as file_ocr_router


app = FastAPI(
    title="Collection Compiler Service",
    version="0.1.0",
    description="Collection Compiler Service 后端接口服务",
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
