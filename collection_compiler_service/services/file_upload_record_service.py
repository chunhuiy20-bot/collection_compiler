from typing import Optional

from common.schemas.CommonResult import Result, PageResult
from collection_compiler_service.model.FileUploadRecord import FileUploadRecord
from collection_compiler_service.repository.FileUploadRecordRepository import FileUploadRecordRepository
from collection_compiler_service.schemas.FileUploadRecordSchema import (
    FileUploadRecordCreateRequest,
    FileUploadRecordVO,
)


class FileUploadRecordService:

    async def create(self, req: FileUploadRecordCreateRequest) -> Result[FileUploadRecordVO]:
        repo = FileUploadRecordRepository(db_name="collection_compiler")
        async with repo as repository:
            existing = await repository.find_by_hash(req.file_hash)
            if existing:
                return Result.success(FileUploadRecordVO.model_validate(existing))

            entity = FileUploadRecord(**req.model_dump(exclude_none=True))
            saved = await repository.save(entity)
        return Result.success(FileUploadRecordVO.model_validate(saved))

    async def find_by_hash(self, file_hash: str) -> Result[Optional[FileUploadRecordVO]]:
        repo = FileUploadRecordRepository(db_name="collection_compiler")
        async with repo as repository:
            entity = await repository.find_by_hash(file_hash)
        if entity is None:
            return Result.success(None)
        return Result.success(FileUploadRecordVO.model_validate(entity))

    async def page_by_type(self, page: int, page_size: int, file_type: Optional[str]) -> Result[PageResult[FileUploadRecordVO]]:
        repo = FileUploadRecordRepository(db_name="collection_compiler")
        async with repo as repository:
            raw = await repository.page_by_type(page, page_size, file_type)
        items = [FileUploadRecordVO.model_validate(item) for item in raw["items"]]
        return Result.success(PageResult[FileUploadRecordVO](
            total=raw["total"], page=raw["page"], page_size=raw["page_size"], items=items
        ))


file_upload_record_service = FileUploadRecordService()
