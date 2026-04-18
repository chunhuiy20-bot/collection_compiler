from typing import Any, Optional, List

from fastapi import File, Form, Query, UploadFile
from fastapi.responses import StreamingResponse

from common.schemas.CommonResult import Result, PageResult
from common.utils.router.CustomRouter import CustomAPIRouter
from ..schemas.CaseAssignmentDetailSchema import CaseAssignmentDetailPatchRequest, CaseAssignmentDetailVO, CasePageQueryRequest
from ..services.excel_upload_service import excel_upload_service
from ..services.case_assignment_detail_service import case_assignment_detail_service

router = CustomAPIRouter(
    prefix="/api/v1/excel",
    tags=["Excel上传"],
    auto_log=True,
    logger_name="collection-compiler-service",
)


@router.post("/upload", summary="上传解析Excel")
async def upload_excel(
    file: UploadFile = File(...),
    file_hash: Optional[str] = Form(None),
) -> Result[Any]:
    file_bytes = await file.read()
    return await excel_upload_service.process_excel_bytes(file_bytes, file.filename or "upload.xlsx", file_hash)


@router.patch("/case", summary="修改缺失数据并重新校验")
async def patch_case(req: CaseAssignmentDetailPatchRequest) -> dict[str, Any]:
    return await excel_upload_service.patch_and_validate(req)


@router.get("/cases", summary="分页查询分案明细")
async def list_cases(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    disposal_type: Optional[str] = Query(default=None),
    case_status: Optional[int] = Query(default=None),
) -> Result[PageResult[CaseAssignmentDetailVO]]:
    req = CasePageQueryRequest(
        page=page,
        page_size=page_size,
        disposal_type=disposal_type,
        case_status=case_status,
    )
    return await case_assignment_detail_service.page_query(req)


@router.get("/cases/by-hash", summary="根据 file_hash 分页查询分案明细")
async def list_cases_by_hash(
    file_hash: str = Query(...),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    disposal_type: Optional[str] = Query(default=None),
    case_status: Optional[int] = Query(default=None),
) -> Result[PageResult[CaseAssignmentDetailVO]]:
    return await case_assignment_detail_service.page_query_by_file_hash(
        file_hash, page, page_size, disposal_type, case_status
    )


@router.get("/cases/abnormal", summary="根据 file_hash 分页查询异常数据(case_status < 0)")
async def list_abnormal_cases(
    file_hash: str = Query(...),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
) -> Result[PageResult[CaseAssignmentDetailVO]]:
    return await case_assignment_detail_service.page_abnormal_by_file_hash(file_hash, page, page_size)
from pydantic import BaseModel

class ExportRequest(BaseModel):
    file_hash: str
    exclude_ids: List[str] = []
    order: str = "asc"
    sort_by: str = "case_status"


@router.post("/cases/export", summary="导出分案明细 Excel")
async def export_cases(req: ExportRequest) -> StreamingResponse:
    buffer, filename = await excel_upload_service.export_excel(req.file_hash, req.exclude_ids, req.order, req.sort_by)
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename}"},
    )