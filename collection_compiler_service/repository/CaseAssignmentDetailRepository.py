from typing import Optional

from sqlalchemy import and_, case, select, func
from sqlalchemy.ext.asyncio import AsyncSession

from common.utils.db.mysql.AsyncBaseRepository import AsyncBaseRepository
from common.utils.db.mysql.MultiAsyncDBManager import multi_db
from collection_compiler_service.config.ServiceConfig import stock_service_config
from collection_compiler_service.model.CaseAssignmentDetail import CaseAssignmentDetail

# 数据库只注册一次，避免每次实例化时重复创建引擎导致连接池泄漏
if "collection_compiler" not in multi_db.databases:
    multi_db.add_database("collection_compiler", stock_service_config.mysql_config_async)


class CaseAssignmentDetailRepository(AsyncBaseRepository[CaseAssignmentDetail]):
    """分案明细数据访问层"""

    def __init__(self, db: Optional[AsyncSession] = None, db_name: Optional[str] = None):
        super().__init__(db, CaseAssignmentDetail, db_name)

    async def save_batch_data(self, items: list[dict]) -> list[CaseAssignmentDetail]:
        """批量插入分案明细数据"""
        entities = [CaseAssignmentDetail(**item) for item in items]
        return await self.save_batch(entities)

    async def page_by_filter(
        self,
        page: int,
        page_size: int,
        disposal_type: Optional[str] = None,
        case_status: Optional[int] = None,
    ) -> dict:
        """分页查询，支持 disposal_type / case_status 筛选
        排序：case_status == 2 优先，其次按 case_id 升序
        """
        m = CaseAssignmentDetail
        conditions = [m.del_flag == 0]
        if disposal_type is not None:
            conditions.append(m.disposal_type == disposal_type)
        if case_status is not None:
            conditions.append(m.case_status == case_status)

        where_clause = and_(*conditions)

        # 总数
        count_stmt = select(func.count(m.id)).where(where_clause)
        count_result = await self.db.execute(count_stmt)
        total = count_result.scalar()

        # 排序：case_status == 2 排最前，其余按 case_id 升序
        priority = case((m.case_status == 2, 0), else_=1)
        data_stmt = (
            select(m)
            .where(where_clause)
            .order_by(priority, m.case_id)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        data_result = await self.db.execute(data_stmt)
        items = list(data_result.scalars().all())

        return {"total": total, "page": page, "page_size": page_size, "items": items}

    async def find_by_hash_exclude_ids(self, file_hash: str, exclude_ids: list[str], order: str = "asc", sort_by: str = "case_status") -> list[CaseAssignmentDetail]:
        m = CaseAssignmentDetail
        conditions = [m.del_flag == 0, m.file_hash == file_hash]
        if exclude_ids:
            conditions.append(m.id.notin_(exclude_ids))
        col = getattr(m, sort_by, m.case_status)
        sort = col.asc() if order == "asc" else col.desc()
        result = await self.db.execute(select(m).where(and_(*conditions)).order_by(sort))
        return list(result.scalars().all())

    async def page_by_file_hash(
        self,
        file_hash: str,
        page: int,
        page_size: int,
        disposal_type: Optional[str] = None,
        case_status: Optional[int] = None,
    ) -> dict:
        m = CaseAssignmentDetail
        conditions = [m.del_flag == 0, m.file_hash == file_hash]
        if disposal_type is not None:
            conditions.append(m.disposal_type == disposal_type)
        if case_status is not None:
            conditions.append(m.case_status == case_status)

        where_clause = and_(*conditions)
        total = (await self.db.execute(select(func.count(m.id)).where(where_clause))).scalar()
        items = list((await self.db.execute(
            select(m).where(where_clause).order_by(m.case_status.asc()).offset((page - 1) * page_size).limit(page_size)
        )).scalars().all())
        return {"total": total, "page": page, "page_size": page_size, "items": items}

    async def page_abnormal_by_file_hash(self, file_hash: str, page: int, page_size: int) -> dict:
        m = CaseAssignmentDetail
        where_clause = and_(m.del_flag == 0, m.file_hash == file_hash, m.case_status < 0)
        total = (await self.db.execute(select(func.count(m.id)).where(where_clause))).scalar()
        items = list((await self.db.execute(
            select(m).where(where_clause).order_by(m.case_status.asc()).offset((page - 1) * page_size).limit(page_size)
        )).scalars().all())
        return {"total": total, "page": page, "page_size": page_size, "items": items}