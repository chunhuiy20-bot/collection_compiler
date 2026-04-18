# 文件名: FileUploadRecord.py

from sqlalchemy import (
    Column,
    String,
    BigInteger,
    Index,
)
from common.model.BaseDBModel import BaseDBModel


class FileUploadRecord(BaseDBModel):
    """文件上传记录表"""
    __tablename__ = "file_upload_record"

    file_hash = Column(String(128), nullable=False, unique=True, comment="文件hash值")
    filename = Column(String(512), nullable=False, comment="文件名称")
    file_path = Column(String(512), nullable=False, comment="文件存储路径")
    file_size = Column(BigInteger, nullable=True, comment="文件大小(字节)")
    file_type = Column(String(32), nullable=True, comment="文件类型:excel/zip/other")
    uploader_id = Column(BigInteger, nullable=True, comment="上传人ID")

    __table_args__ = (
        Index("idx_file_upload_hash", "file_hash"),
        Index("idx_file_upload_uploader", "uploader_id"),
    )
