from typing import Optional
from pydantic import BaseModel, ConfigDict, field_serializer


class FileUploadRecordCreateRequest(BaseModel):
    file_hash: str
    filename: str
    file_path: str
    file_size: Optional[int] = None
    file_type: Optional[str] = None
    uploader_id: Optional[int] = None


class FileUploadRecordVO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    file_hash: str
    filename: str
    file_path: str
    file_size: Optional[int] = None
    file_type: Optional[str] = None
    uploader_id: Optional[int] = None

    @field_serializer("id")
    def serialize_id(self, v: int) -> str:
        return str(v)

    @field_serializer("uploader_id")
    def serialize_uploader_id(self, v: Optional[int]) -> Optional[str]:
        return str(v) if v is not None else None
