# 文件名: CaseAssignmentDetail.py

from sqlalchemy import (
    Column,
    String,
    BigInteger,
    Date,
    Numeric,
    Integer,
    Index,
    JSON,
)
from sqlalchemy.ext.mutable import MutableList
from common.model.BaseDBModel import BaseDBModel


class CaseAssignmentDetail(BaseDBModel):
    """分案明细表"""
    __tablename__ = "case_assignment_detail"

    # 业务字段（来自 xlsx）
    case_id = Column(BigInteger, nullable=True, unique=True, comment="案件ID")
    debtor_name = Column(String(32), nullable=True, comment="姓名")
    uid = Column(String(32), nullable=True, comment="UID")
    household_address = Column(String(128), nullable=True, comment="户籍地")
    application_code = Column(String(32), nullable=True, comment="进件编码")
    transfer_notice_url = Column(String(255), nullable=True, comment="债转公告链接")
    transfer_notice_no = Column(String(64), nullable=True, comment="债转公告序号")
    transfer_agreement_no = Column(String(64), nullable=True, comment="债转协议序号")
    project_name = Column(String(64), nullable=True, comment="项目名称")
    province = Column(String(16), nullable=True, comment="省")
    city = Column(String(32), nullable=True, comment="市")
    entrust_date = Column(Date, nullable=True, comment="委案日期")
    entrust_batch_no = Column(String(32), nullable=True, comment="委案批次号")
    entrust_org = Column(String(64), nullable=True, comment="委案机构")
    entrusted_principal_balance = Column(Numeric(14, 2), nullable=True, comment="委案剩本金额")
    entrusted_total_claim = Column(Numeric(14, 2), nullable=True, comment="委案债权总额")
    disposal_type = Column(String(8), nullable=True, comment="处置方式(保全/散诉)")
    case_status = Column(Integer, nullable=False, default=0, comment="案件状态:0待处理 1处理中 2处理已完成 3处理失败 -1警告缺失 -2严重缺失")
    case_followers = Column(
        MutableList.as_mutable(JSON),
        nullable=False,
        default=list,
        comment="案件跟进人数组",
    )
    file_hash = Column(String(128), nullable=True, comment="来源文件hash")

    __table_args__ = (
        Index("idx_case_assign_uid", "uid"),
        Index("idx_case_assign_batch_disposal", "entrust_batch_no", "disposal_type"),
        Index("idx_case_assign_entrust_date", "entrust_date"),
        Index("idx_case_assign_project", "project_name"),
        Index("idx_case_assign_status", "case_status"),
        Index("idx_case_assign_file_hash", "file_hash"),
    )
