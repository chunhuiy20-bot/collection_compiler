"""
File: case_assignment_detail_service.py
Description: Case assignment detail service for batch insert with duplicate case_id ignored
"""

from typing import Optional

from sqlalchemy.dialects.mysql import insert

from common.schemas.CommonResult import Result, PageResult
from common.utils.decorators.AsyncDecorators import async_retry
from common.utils.decorators.WithRepoDecorators import with_repo
from collection_compiler_service.model.CaseAssignmentDetail import CaseAssignmentDetail
from collection_compiler_service.repository.CaseAssignmentDetailRepository import CaseAssignmentDetailRepository
from collection_compiler_service.schemas.CaseAssignmentDetailSchema import CaseAssignmentDetailVO, CasePageQueryRequest


class CaseAssignmentDetailService:
    """Case assignment detail service"""

    @async_retry(max_retries=3, delay=1.0)
    @with_repo(CaseAssignmentDetailRepository, db_name="collection_compiler")
    async def save_batch_data(
        self,
        repo: CaseAssignmentDetailRepository,
        items: list[dict],
    ) -> Result[int]:
        """Batch insert case assignment details and ignore duplicated case_id"""
        try:
            if not items:
                return Result.success(0)

            stmt = insert(CaseAssignmentDetail).prefix_with("IGNORE").values(items)
            async with repo as repository:
                result = await repository.db.execute(stmt)

            return Result.success(result.rowcount)
        except Exception as e:
            return Result.fail(f"Batch insert case assignment detail failed: {str(e)}")

    async def page_query(self, req: CasePageQueryRequest) -> Result[PageResult[CaseAssignmentDetailVO]]:
        repo = CaseAssignmentDetailRepository(db_name="collection_compiler")
        async with repo as repository:
            raw = await repository.page_by_filter(
                page=req.page,
                page_size=req.page_size,
                disposal_type=req.disposal_type,
                case_status=req.case_status,
            )

        items = [CaseAssignmentDetailVO.model_validate(item) for item in raw["items"]]
        page_result = PageResult[CaseAssignmentDetailVO](
            total=raw["total"],
            page=raw["page"],
            page_size=raw["page_size"],
            items=items,
        )
        return Result.success(page_result)


    async def page_query_by_file_hash(
        self,
        file_hash: str,
        page: int,
        page_size: int,
        disposal_type: Optional[str] = None,
        case_status: Optional[int] = None,
    ) -> Result[PageResult[CaseAssignmentDetailVO]]:
        repo = CaseAssignmentDetailRepository(db_name="collection_compiler")
        async with repo as repository:
            raw = await repository.page_by_file_hash(file_hash, page, page_size, disposal_type, case_status)
        items = [CaseAssignmentDetailVO.model_validate(item) for item in raw["items"]]
        return Result.success(PageResult[CaseAssignmentDetailVO](
            total=raw["total"], page=raw["page"], page_size=raw["page_size"], items=items
        ))


    async def page_abnormal_by_file_hash(
        self,
        file_hash: str,
        page: int,
        page_size: int,
    ) -> Result[PageResult[CaseAssignmentDetailVO]]:
        repo = CaseAssignmentDetailRepository(db_name="collection_compiler")
        async with repo as repository:
            raw = await repository.page_abnormal_by_file_hash(file_hash, page, page_size)
        items = [CaseAssignmentDetailVO.model_validate(item) for item in raw["items"]]
        return Result.success(PageResult[CaseAssignmentDetailVO](
            total=raw["total"], page=raw["page"], page_size=raw["page_size"], items=items
        ))


case_assignment_detail_service = CaseAssignmentDetailService()
