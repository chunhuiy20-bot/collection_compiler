from decimal import Decimal
from datetime import date
from typing import Optional
from pydantic import BaseModel, ConfigDict, field_serializer


class CaseAssignmentDetailPatchRequest(BaseModel):
    id: int
    case_id: Optional[int] = None
    debtor_name: Optional[str] = None
    uid: Optional[str] = None
    household_address: Optional[str] = None
    application_code: Optional[str] = None
    transfer_notice_url: Optional[str] = None
    transfer_notice_no: Optional[str] = None
    transfer_agreement_no: Optional[str] = None
    project_name: Optional[str] = None
    province: Optional[str] = None
    city: Optional[str] = None
    entrust_date: Optional[date] = None
    entrust_batch_no: Optional[str] = None
    entrust_org: Optional[str] = None
    entrusted_principal_balance: Optional[Decimal] = None
    entrusted_total_claim: Optional[Decimal] = None
    disposal_type: Optional[str] = None


class CaseAssignmentDetailVO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    case_id: Optional[int] = None
    debtor_name: Optional[str] = None
    uid: Optional[str] = None
    household_address: Optional[str] = None
    application_code: Optional[str] = None
    transfer_notice_url: Optional[str] = None
    transfer_notice_no: Optional[str] = None
    transfer_agreement_no: Optional[str] = None
    project_name: Optional[str] = None
    province: Optional[str] = None
    city: Optional[str] = None
    entrust_date: Optional[date] = None
    entrust_batch_no: Optional[str] = None
    entrust_org: Optional[str] = None
    entrusted_principal_balance: Optional[Decimal] = None
    entrusted_total_claim: Optional[Decimal] = None
    disposal_type: Optional[str] = None
    case_status: int = 0
    file_hash: Optional[str] = None

    @field_serializer("id")
    def serialize_id(self, v: int) -> str:
        return str(v)


class CasePageQueryRequest(BaseModel):
    page: int = 1
    page_size: int = 20
    disposal_type: Optional[str] = None
    case_status: Optional[int] = None
