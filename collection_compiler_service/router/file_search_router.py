import mimetypes
from pathlib import Path
from typing import Any

from fastapi import HTTPException
from fastapi.responses import FileResponse

from common.schemas.CommonResult import Result
from common.utils.router.CustomRouter import CustomAPIRouter
from ..services.file_search_service import file_search_service

router = CustomAPIRouter(
    prefix="/api/v1/files",
    tags=["文件查询"],
    auto_log=True,
    logger_name="collection-compiler-service",
)


@router.get("/search", summary="根据 application_code 或 uid 查询文件")
async def search_files(
    application_code: str | None = None,
    uid: str | None = None,
) -> Result[Any]:
    if not application_code and not uid:
        raise HTTPException(status_code=400, detail="application_code 或 uid 至少传一个")
    files = file_search_service.find_files(application_code, uid)
    return Result.success(files)


@router.get("/preview", summary="预览文件（图片可直接展示）")
async def preview_file(path: str):
    try:
        target = file_search_service.resolve_preview_path(path)
    except FileNotFoundError as err:
        raise HTTPException(status_code=404, detail=str(err)) from err
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err)) from err

    media_type, _ = mimetypes.guess_type(str(target))
    filename = Path(target).name
    return FileResponse(path=target, media_type=media_type or "application/octet-stream", filename=filename)
