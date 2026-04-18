from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from common.utils.db.mysql.AsyncBaseRepository import AsyncBaseRepository
from common.utils.db.mysql.MultiAsyncDBManager import multi_db
from collection_compiler_service.config.ServiceConfig import stock_service_config
from collection_compiler_service.model.FileUploadRecord import FileUploadRecord

if "collection_compiler" not in multi_db.databases:
    multi_db.add_database("collection_compiler", stock_service_config.mysql_config_async)


class FileUploadRecordRepository(AsyncBaseRepository[FileUploadRecord]):

    def __init__(self, db: Optional[AsyncSession] = None, db_name: Optional[str] = None):
        super().__init__(db, FileUploadRecord, db_name)

    async def find_by_hash(self, file_hash: str) -> Optional[FileUploadRecord]:
        stmt = select(FileUploadRecord).where(
            FileUploadRecord.file_hash == file_hash,
            FileUploadRecord.del_flag == 0,
        )
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def page_by_type(self, page: int, page_size: int, file_type: Optional[str]) -> dict:
        conditions = [FileUploadRecord.del_flag == 0]
        if file_type:
            conditions.append(FileUploadRecord.file_type == file_type)

        count_stmt = select(func.count(FileUploadRecord.id)).where(*conditions)
        total = (await self.db.execute(count_stmt)).scalar()

        data_stmt = (
            select(FileUploadRecord)
            .where(*conditions)
            .order_by(FileUploadRecord.create_time.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        items = list((await self.db.execute(data_stmt)).scalars().all())
        return {"total": total, "page": page, "page_size": page_size, "items": items}
