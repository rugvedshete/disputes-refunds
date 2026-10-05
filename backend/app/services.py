"""Business logic. Every mutating function: lock the dispute row, validate the
transition, write the change + audit row, commit once (all-or-nothing)."""
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, contains_eager

from .errors import Conflict, Forbidden, IdempotencyKeyReused, NotFound
from .models import AuditLog, Dispute, Evidence, Refund, Resolution, Role, Status, User
from .state_machine import assert_transition, can_add_evidence


def _audit(db: Session, d: Dispute, actor: User, action: str, from_s: str | None, to_s: str, note: str | None = None):
    db.add(
        AuditLog(
            dispute_id=d.id, actor_id=actor.id, actor_role=actor.role,
            action=action, from_status=from_s, to_status=to_s, note=note,
        )
    )


def _load(db: Session, user: User, dispute_id: int, lock: bool = False) -> Dispute:
    stmt = select(Dispute).where(Dispute.id == dispute_id)
    if lock:
        stmt = stmt.with_for_update()  # SELECT ... FOR UPDATE: concurrent writers queue here
    d = db.scalar(stmt)
    # Customers get a 404 (not 403) for other people's disputes so ids can't be probed.
    if d is None or (user.role == Role.customer.value and d.customer_id != user.id):
        raise NotFound("Dispute not found")
    return d


def get_dispute(db: Session, user: User, dispute_id: int) -> Dispute:
    return _load(db, user, dispute_id)


def list_disputes(db: Session, user: User, status: Status | None, q: str | None, limit: int, offset: int):
    filters = []
    if user.role == Role.customer.value:
        filters.append(Dispute.customer_id == user.id)
    if status:
        filters.append(Dispute.status == status.value)
    if q and q.strip():
        like = f"%{q.strip()}%"
        conds = [Dispute.order_ref.ilike(like), Dispute.reason.ilike(like), User.email.ilike(like)]
        if q.strip().isdigit():
            conds.append(Dispute.id == int(q.strip()))
        filters.append(or_(*conds))
    total = db.scalar(select(func.count()).select_from(Dispute).join(Dispute.customer).where(*filters))
    rows = (
        db.scalars(
            select(Dispute).join(Dispute.customer).where(*filters)
            .options(contains_eager(Dispute.customer))
            .order_by(Dispute.id.desc()).limit(limit).offset(offset)
        )
        .unique()
        .all()
    )
    return rows, total or 0


def open_dispute(db: Session, customer: User, order_ref: str, amount_cents: int, reason: str) -> Dispute:
    d = Dispute(customer_id=customer.id, order_ref=order_ref, amount_cents=amount_cents,
                reason=reason, status=Status.opened.value)
    db.add(d)
    db.flush()
    _audit(db, d, customer, "opened", None, Status.opened.value)
    db.commit()
    return d


def add_evidence(db: Session, user: User, dispute_id: int, description: str) -> Dispute:
    if user.role != Role.customer.value:
        raise Forbidden("Only the customer can submit evidence")
    d = _load(db, user, dispute_id, lock=True)
    if not can_add_evidence(d.status):
        raise Conflict("Evidence can no longer be added once review has started")
    db.add(Evidence(dispute_id=d.id, submitted_by=user.id, description=description))
    if d.status == Status.opened.value:
        assert_transition(d.status, Status.evidence_submitted)
        _audit(db, d, user, "evidence_submitted", d.status, Status.evidence_submitted.value)
        d.status = Status.evidence_submitted.value
    else:
        _audit(db, d, user, "evidence_added", d.status, d.status)
    db.commit()
    db.refresh(d)
    return d


def start_review(db: Session, agent: User, dispute_id: int) -> Dispute:
    d = _load(db, agent, dispute_id, lock=True)
    assert_transition(d.status, Status.under_review)
    _audit(db, d, agent, "review_started", d.status, Status.under_review.value)
    d.status = Status.under_review.value
    db.commit()
    db.refresh(d)
    return d


def refund_dispute(db: Session, agent: User, dispute_id: int, idempotency_key: str) -> tuple[Dispute, Refund, bool]:
    """Returns (dispute, refund, replayed). Safe to retry with the same key."""
    d = _load(db, agent, dispute_id, lock=True)  # serialises concurrent refund attempts

    # Checked AFTER taking the lock, so a racing duplicate sees the winner's committed row.
    existing = db.scalar(select(Refund).where(Refund.idempotency_key == idempotency_key))
    if existing:
        if existing.dispute_id != d.id:
            raise IdempotencyKeyReused("This Idempotency-Key was already used for a different dispute")
        return d, existing, True

    if d.status == Status.resolved.value:
        raise Conflict("Dispute is already resolved")
    assert_transition(d.status, Status.resolved)

    refund = Refund(dispute_id=d.id, idempotency_key=idempotency_key,
                    amount_cents=d.amount_cents, issued_by=agent.id)
    db.add(refund)
    _audit(db, d, agent, "refund_approved", d.status, Status.resolved.value,
           note=f"refund of {d.amount_cents} cents")
    d.status = Status.resolved.value
    d.resolution = Resolution.refund.value
    try:
        db.commit()  # UNIQUE(dispute_id) / UNIQUE(key) are the backstop if anything slips past
    except IntegrityError:
        db.rollback()
        raise Conflict("Refund already applied or idempotency key already in use")
    db.refresh(refund)
    db.refresh(d)
    return d, refund, False


def reject_dispute(db: Session, agent: User, dispute_id: int, note: str) -> Dispute:
    d = _load(db, agent, dispute_id, lock=True)
    if d.status == Status.resolved.value:
        raise Conflict("Dispute is already resolved")
    assert_transition(d.status, Status.resolved)
    _audit(db, d, agent, "rejected", d.status, Status.resolved.value, note=note)
    d.status = Status.resolved.value
    d.resolution = Resolution.reject.value
    d.resolution_note = note
    db.commit()
    db.refresh(d)
    return d
