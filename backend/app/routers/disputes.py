from fastapi import APIRouter, Depends, Header, Query, Response
from sqlalchemy.orm import Session

from .. import services
from ..db import get_db
from ..deps import current_user, require_agent, require_customer
from ..models import Status, User
from ..schemas import (DisputeCreate, DisputeDetail, DisputeList, DisputeOut, EvidenceCreate,
                       RefundOut, RejectIn)

router = APIRouter(prefix="/disputes", tags=["disputes"])


def _detail(d) -> DisputeDetail:
    return DisputeDetail.model_validate(d)


@router.post("", response_model=DisputeOut, status_code=201)
def create(body: DisputeCreate, user: User = Depends(require_customer), db: Session = Depends(get_db)):
    d = services.open_dispute(db, user, body.order_ref, body.amount_cents, body.reason)
    return DisputeOut.model_validate(d)


@router.get("", response_model=DisputeList)
def list_disputes(
    status: Status | None = None,
    q: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    rows, total = services.list_disputes(db, user, status, q, limit, offset)
    return DisputeList(items=[DisputeOut.model_validate(r) for r in rows], total=total)


@router.get("/{dispute_id}", response_model=DisputeDetail)
def get(dispute_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    return _detail(services.get_dispute(db, user, dispute_id))


@router.post("/{dispute_id}/evidence", response_model=DisputeDetail)
def add_evidence(dispute_id: int, body: EvidenceCreate, user: User = Depends(current_user),
                 db: Session = Depends(get_db)):
    return _detail(services.add_evidence(db, user, dispute_id, body.description))


@router.post("/{dispute_id}/review", response_model=DisputeDetail)
def start_review(dispute_id: int, user: User = Depends(require_agent), db: Session = Depends(get_db)):
    return _detail(services.start_review(db, user, dispute_id))


@router.post("/{dispute_id}/refund", response_model=RefundOut, status_code=201)
def refund(
    dispute_id: int,
    response: Response,
    idempotency_key: str = Header(..., alias="Idempotency-Key", min_length=8, max_length=128),
    user: User = Depends(require_agent),
    db: Session = Depends(get_db),
):
    _, r, replayed = services.refund_dispute(db, user, dispute_id, idempotency_key)
    if replayed:
        response.status_code = 200
        response.headers["Idempotent-Replay"] = "true"
    return RefundOut.model_validate(r).model_copy(update={"replayed": replayed})


@router.post("/{dispute_id}/reject", response_model=DisputeDetail)
def reject(dispute_id: int, body: RejectIn, user: User = Depends(require_agent), db: Session = Depends(get_db)):
    return _detail(services.reject_dispute(db, user, dispute_id, body.note))
