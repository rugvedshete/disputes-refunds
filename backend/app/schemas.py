from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from .models import Resolution, Status


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    email: str
    role: str


class DisputeCreate(BaseModel):
    order_ref: str = Field(min_length=1, max_length=64)
    amount_cents: int = Field(gt=0)
    reason: str = Field(min_length=3, max_length=2000)


class EvidenceCreate(BaseModel):
    description: str = Field(min_length=3, max_length=4000)


class RejectIn(BaseModel):
    note: str = Field(min_length=3, max_length=2000)


class EvidenceOut(ORM):
    id: int
    submitted_by: int
    description: str
    created_at: datetime


class AuditOut(ORM):
    id: int
    action: str
    from_status: str | None
    to_status: str
    note: str | None
    actor_id: int
    actor_email: str
    actor_role: str
    created_at: datetime


class RefundOut(ORM):
    id: int
    dispute_id: int
    amount_cents: int
    idempotency_key: str
    issued_by: int
    created_at: datetime
    replayed: bool = False


class DisputeOut(ORM):
    id: int
    customer_id: int
    customer_email: str
    order_ref: str
    amount_cents: int
    reason: str
    status: Status
    resolution: Resolution | None
    resolution_note: str | None
    created_at: datetime
    updated_at: datetime


class DisputeDetail(DisputeOut):
    evidence: list[EvidenceOut]
    audit_logs: list[AuditOut]
    refund: RefundOut | None


class DisputeList(BaseModel):
    items: list[DisputeOut]
    total: int
