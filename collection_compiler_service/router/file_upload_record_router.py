from typing import Optional

from fastapi import Query

from common.schemas.CommonResult import Result, PageResult
from common.utils.router.CustomRouter import CustomAPIRouter
from ..schemas.FileUploadRecordSchema import (
    FileUploadRecordCreateRequest,
    FileUploadRecordVO,
)
from ..services.file_upload_record_service import file_upload_record_service

router = CustomAPIRouter(
    prefix="/api/v1/file-record",
    tags=["文件上传记录"],
    auto_log=True,
    logger_name="collection-compiler-service",
)


@router.post("", summary="新增上传记录")
async def create_record(req: FileUploadRecordCreateRequest) -> Result[FileUploadRecordVO]:
    return await file_upload_record_service.create(req)


@router.get("/page", summary="分页查询上传记录")
async def page_records(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    file_type: Optional[str] = Query(default=None),
) -> Result[PageResult[FileUploadRecordVO]]:
    return await file_upload_record_service.page_by_type(page, page_size, file_type)


@router.get("/{file_hash}", summary="根据 file_hash 查询上传记录")
async def get_by_hash(file_hash: str) -> Result[Optional[FileUploadRecordVO]]:
    return await file_upload_record_service.find_by_hash(file_hash)
